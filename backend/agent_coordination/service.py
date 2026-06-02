"""AgentService — the governed orchestration hub for the Agent Coordination Framework.

Ties identity, taxonomy, capabilities, lifecycle, governance, assignments, registry,
audit, and lineage into the use cases that declare an Agent, govern its capabilities,
assign it to work, and move it through its lifecycle. Every mutation is:
governance-gated -> audited (immutable) -> lineage-extended -> version-bumped ->
registry-synced.

An **Agent** describes capability and holds no autonomous authority. The transition
into AVAILABLE (and the other governed transitions) requires a **policy decision**:
the service calls an injected ``policy_decider`` (the V4-P2 policy engine, wired by
the integration layer). If none is injected, governed transitions require an explicit
caller ``approved=True``. **Every assignment must satisfy the target's capability
requirements** (Task<->Agent integration) and never implies execution. Shares the
platform's single ``ml.lineage.LineageTracker`` and the shared ``ImmutableAuditLog``
— no parallel lineage/audit/governance.
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence

from ml.lineage import LineageTracker  # allowed: backend -> ml

from .version import DETERMINISTIC_EPOCH
from .identity import mint_agent, mint_relationship, mint_assignment
from .taxonomy import (
    validate_category, validate_relation, is_priority, is_assignment_target, AgentPriority,
    AssignmentState, TaxonomyError,
)
from .lifecycle import AgentLifecycle, AgentLifecycleState
from .governance import AgentGovernanceGate, AgentGovernanceError
from .registry import AgentRegistry
from .validation import AgentValidator
from .audit import make_agent_audit_log
from .capabilities import satisfies, requires_capability_approval
from .lineage import make_agent_lineage, make_assignment_lineage, make_relationship_lineage
from .models.domain import (
    AgentMetadata, AgentCapability, AgentAssignment, AgentGovernanceRecord,
    AgentConstraintReference, AgentRelationship, AgentVersion, AgentRegistryRecord, AgentRecord,
)
from .reports import (
    build_agent_summary_report, build_capability_report, build_assignment_report,
    build_agent_lifecycle_report, build_agent_governance_report, build_agent_validation_report,
    build_agent_audit_report, build_agent_lineage_report,
)

# A policy decider takes (hook, agent) and returns (approved, decision, policy_id, authority).
PolicyDecider = Callable[[str, AgentRecord], tuple]


class AgentCapabilityError(RuntimeError):
    """Raised when an assignment's capability requirements are not satisfied."""



class AgentService:
    """Stateful service: agent registry, shared lineage tracker, immutable audit log."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[AgentRegistry] = None,
                 policy_decider: Optional[PolicyDecider] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or AgentRegistry()
        self.audit = make_agent_audit_log()
        self.lifecycle = AgentLifecycle()
        self.gate = AgentGovernanceGate()
        self.validator = AgentValidator()
        self.policy_decider = policy_decider

    # --- create ---------------------------------------------------------------
    def create_agent(self, *, category: str, agent_key: str, metadata: AgentMetadata,
                     capabilities: Sequence[AgentCapability] = (),
                     priority: str = AgentPriority.MEDIUM, derived_from: Sequence[str] = (),
                     owner: str = "agent-ops",
                     created_at: str = DETERMINISTIC_EPOCH) -> AgentRecord:
        """Create a PROPOSED agent (a governed participant), governance-gated + lineage-rooted."""
        validate_category(category)
        if not is_priority(priority):
            raise ValueError(f"invalid agent priority {priority!r}")
        ident = mint_agent(category, agent_key)
        agent = AgentRecord(
            agent_id=ident.id, category=category, agent_key=agent_key, metadata=metadata,
            priority=priority, state=AgentLifecycleState.PROPOSED,
            governance=AgentGovernanceRecord(), capabilities=tuple(capabilities), owner=owner,
            created_at=created_at)

        parents = list(derived_from)
        report = self.gate.evaluate(agent=agent, parents=tuple(parents),
                                    requires_lineage=len(parents) > 0)
        self.gate.raise_if_failed(report)

        node = self.lineage.record(make_agent_lineage(
            agent.agent_id, parents=parents, category=category, reason="created",
            created_at=created_at))
        self.audit.append("agent_created",
                          {"agent_id": agent.agent_id, "category": category,
                           "lineage_id": node.lineage_id, "n_capabilities": len(capabilities),
                           "n_parents": len(parents)}, created_at=created_at)
        agent.lineage_id = node.lineage_id
        self._finalize(agent, reason="created", created_at=created_at)
        return agent

    # --- capability governance -----------------------------------------------
    def approve_capabilities(self, agent: AgentRecord, *, authority: str = "governance",
                             created_at: str = DETERMINISTIC_EPOCH) -> AgentRecord:
        """Mark the agent's high/critical-risk capabilities approved (governance act)."""
        approved_caps = tuple(
            AgentCapability(name=c.name, mode=c.mode, risk=c.risk, description=c.description,
                            depends_on=c.depends_on, constraint_ids=c.constraint_ids,
                            approved=True, capability_version=c.capability_version)
            for c in agent.capabilities)
        agent.capabilities = approved_caps
        agent.governance = agent.governance.with_event(
            approval_state=agent.governance.approval_state, authority=authority,
            hook="agent_capability_approval", decision="approved", policy_id=None,
            created_at=created_at, capability_approved=True)
        self.audit.append("agent_capabilities_approved",
                          {"agent_id": agent.agent_id, "authority": authority,
                           "n_capabilities": len(approved_caps)}, created_at=created_at)
        self._finalize(agent, reason="capabilities_approved", created_at=created_at)
        return agent

    def attach_constraint(self, agent: AgentRecord, constraint: AgentConstraintReference,
                          created_at: str = DETERMINISTIC_EPOCH) -> AgentRecord:
        agent.constraints = agent.constraints + (constraint,)
        agent.governance = agent.governance.with_constraint(constraint.constraint_id)
        self.audit.append("agent_constraint_attached",
                          {"agent_id": agent.agent_id, "constraint_id": constraint.constraint_id,
                           "hook": constraint.hook}, created_at=created_at)
        self._finalize(agent, reason=f"attach_constraint:{constraint.constraint_id}",
                       created_at=created_at)
        return agent

    # --- relationships --------------------------------------------------------
    def relate(self, agent: AgentRecord, *, relation: str, target_id: str, target_kind: str,
               target_lineage_id: Optional[str] = None,
               created_at: str = DETERMINISTIC_EPOCH) -> AgentRelationship:
        """Create a versioned relationship Agent -> target (lineage-tracked)."""
        validate_relation(relation, target_kind)
        rel_id = mint_relationship(agent.agent_id, relation, target_id)
        parents = [agent.lineage_id] + ([target_lineage_id] if target_lineage_id else [])
        node = self.lineage.record(make_relationship_lineage(
            rel_id, parents=parents, relation=relation, created_at=created_at))
        self.audit.append("agent_relationship_added",
                          {"relationship_id": rel_id, "agent_id": agent.agent_id,
                           "relation": relation, "target_id": target_id,
                           "target_kind": target_kind, "lineage_id": node.lineage_id},
                          created_at=created_at)
        version = AgentVersion.compute(f"rel:{rel_id}", None)
        rel = AgentRelationship(relationship_id=rel_id, source_agent_id=agent.agent_id,
                                relation=relation, target_id=target_id, target_kind=target_kind,
                                version=version)
        self.registry.register_relationship(rel)
        return rel



    # --- assignments (Task <-> Agent integration) ----------------------------
    def assign(self, agent: AgentRecord, *, target_id: str, target_kind: str,
               required_capabilities: Sequence[str] = (), target_lineage_id: Optional[str] = None,
               created_at: str = DETERMINISTIC_EPOCH) -> AgentAssignment:
        """Assign an AVAILABLE agent to a work unit — every assignment must satisfy the
        target's capability requirements, and an assignment never implies execution."""
        if not is_assignment_target(target_kind):
            raise TaxonomyError(f"unknown assignment target kind {target_kind!r}")
        if not agent.is_available:
            raise AgentGovernanceError(
                f"agent {agent.agent_id} is not AVAILABLE (state={agent.state.value}); "
                "only available agents may be assigned")
        ok, missing = satisfies(agent, required_capabilities)
        if not ok:
            raise AgentCapabilityError(
                f"agent {agent.agent_id} lacks required capabilities {missing} "
                f"for {target_kind} {target_id}")
        return self._record_assignment(agent, target_id=target_id, target_kind=target_kind,
                                       required_capabilities=required_capabilities,
                                       state=AssignmentState.ASSIGNED,
                                       target_lineage_id=target_lineage_id, created_at=created_at)

    def set_assignment_state(self, agent: AgentRecord, assignment: AgentAssignment, *,
                             state: str, created_at: str = DETERMINISTIC_EPOCH) -> AgentAssignment:
        """Transition an assignment's state (assigned -> blocked/revoked/completed/...)."""
        from .taxonomy import is_assignment_state
        if not is_assignment_state(state):
            raise TaxonomyError(f"unknown assignment state {state!r}")
        return self._record_assignment(
            agent, target_id=assignment.target_id, target_kind=assignment.target_kind,
            required_capabilities=assignment.required_capabilities, state=state,
            target_lineage_id=None, created_at=created_at, previous=assignment)

    def _record_assignment(self, agent, *, target_id, target_kind, required_capabilities, state,
                           target_lineage_id, created_at, previous=None) -> AgentAssignment:
        assignment_id = mint_assignment(agent.agent_id, target_kind, target_id)
        parents = [agent.lineage_id] + ([target_lineage_id] if target_lineage_id else [])
        node = self.lineage.record(make_assignment_lineage(
            assignment_id, parents=parents, target_kind=target_kind, created_at=created_at))
        self.audit.append("agent_assignment",
                          {"assignment_id": assignment_id, "agent_id": agent.agent_id,
                           "target_id": target_id, "target_kind": target_kind, "state": state,
                           "lineage_id": node.lineage_id}, created_at=created_at)
        prev_version = previous.version if previous is not None else None
        sig = {"agent": agent.agent_id, "target": target_id, "kind": target_kind, "state": state}
        version = AgentVersion.compute(str(sig), prev_version)
        assignment = AgentAssignment(
            assignment_id=assignment_id, agent_id=agent.agent_id, target_id=target_id,
            target_kind=target_kind, state=state,
            required_capabilities=tuple(required_capabilities), lineage_id=node.lineage_id,
            version=version)
        self.registry.register_assignment(assignment)
        return assignment

    # --- lifecycle transition (governed) -------------------------------------
    def transition(self, agent: AgentRecord, target: AgentLifecycleState, *, reason: str = "",
                   approved: bool = False, authority: Optional[str] = None,
                   created_at: str = DETERMINISTIC_EPOCH) -> AgentRecord:
        """Move an agent to ``target`` (validated, governed, audited, versioned).

        Governed transitions (APPROVED/AVAILABLE/SUSPENDED/RETIRED) require a policy
        decision. If a ``policy_decider`` is injected it is consulted; otherwise the
        caller must pass ``approved=True``. AVAILABLE additionally fails the gate
        unless approved and (if any high-risk capabilities) capability-approved.
        """
        record = self.lifecycle.transition(agent.state, target, reason=reason,
                                            created_at=created_at)
        decision, policy_id = "n/a", None
        availability_approved = True
        if self.lifecycle.requires_policy(target):
            hook = self.lifecycle.policy_hook(target)
            if self.policy_decider is not None:
                approved, decision, policy_id, authority = self.policy_decider(hook, agent)
            else:
                decision = "approved" if approved else "denied"
            availability_approved = approved
            self.audit.append("agent_policy_decision",
                              {"agent_id": agent.agent_id, "hook": hook, "decision": decision,
                               "policy_id": policy_id, "approved": approved},
                              created_at=created_at)
            if not approved:
                agent.governance = agent.governance.with_event(
                    approval_state="rejected", authority=authority, hook=hook,
                    decision=decision, policy_id=policy_id, created_at=created_at)
                self._finalize(agent, reason=f"policy_denied:{hook}", created_at=created_at)
                raise AgentGovernanceError(
                    f"transition {agent.state.value}->{target.value} denied by policy ({hook})")
            agent.governance = agent.governance.with_event(
                approval_state="approved", authority=authority, hook=hook, decision=decision,
                policy_id=policy_id, created_at=created_at)

        report = self.gate.evaluate(agent=agent, parents=(agent.lineage_id,),
                                    requires_lineage=True, target_state=target,
                                    availability_approved=availability_approved)
        self.gate.raise_if_failed(report)

        self.audit.append("agent_state_change", record.to_dict(), created_at=created_at)
        node = self.lineage.record(make_agent_lineage(
            agent.agent_id, parents=(agent.lineage_id,), category=agent.category,
            reason=f"{record.from_state}->{record.to_state}", created_at=created_at,
            extra={"transition": record.to_dict()}))
        agent.state = target
        agent.lineage_id = node.lineage_id
        self._finalize(agent, reason=f"transition:{record.from_state}->{record.to_state}",
                       created_at=created_at)
        return agent

    # --- validation + reports -------------------------------------------------
    def validate(self, agent: AgentRecord):
        return self.validator.validate(agent=agent, registry=self.registry,
                                       audit_log=self.audit, lineage_tracker=self.lineage)

    def requires_capability_approval(self, agent: AgentRecord) -> bool:
        return requires_capability_approval(agent)

    def reports(self, agents: Sequence) -> dict:
        agents = list(agents)
        return {
            "agent_summary_report": build_agent_summary_report(agents),
            "capability_report": build_capability_report(agents),
            "assignment_report": build_assignment_report(self.registry),
            "agent_lifecycle_report": build_agent_lifecycle_report(agents),
            "agent_governance_report": build_agent_governance_report(agents),
            "agent_audit_report": build_agent_audit_report(self.audit),
            "agent_lineage_report": build_agent_lineage_report(agents, self.lineage),
        }

    def validation_report(self, scope: str, validation_report_dict: dict) -> dict:
        return build_agent_validation_report(scope, validation_report_dict)

    # --- internals ------------------------------------------------------------
    def _finalize(self, agent: AgentRecord, *, reason: str, created_at: str) -> None:
        """Bump the agent version (chained), audit it, then sync the registry."""
        previous = agent.version or None
        new_version = AgentVersion.compute(agent.state_signature(), previous)
        agent.previous_version = previous
        agent.version = new_version
        self.audit.append("agent_version_changed",
                          {"agent_id": agent.agent_id, "version": new_version, "reason": reason},
                          created_at=created_at)
        agent.audit_state = self.audit.head
        self.registry.register(AgentRegistryRecord(
            agent_id=agent.agent_id, category=agent.category, state=agent.state.value,
            priority=agent.priority, version=new_version,
            approval_state=agent.governance.approval_state, capabilities=agent.capability_names,
            assignments=tuple(a.assignment_id for a in self.registry.assignments_for(agent.agent_id)),
            policy_references=agent.governance.policy_references, lineage_id=agent.lineage_id,
            audit_state=agent.audit_state, content_signature_value=agent.state_signature()))
        self.audit.append("agent_registered",
                          {"agent_id": agent.agent_id, "version": new_version},
                          created_at=created_at)
        agent.audit_state = self.audit.head
