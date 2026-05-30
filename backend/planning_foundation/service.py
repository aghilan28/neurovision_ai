"""PlanService — the governed orchestration hub for the Planning Foundation.

Ties identity, taxonomy, lifecycle, governance, dependencies, registry, audit, and
lineage into the use cases that derive a Plan from an approved Goal, relate plans,
and move a plan through its lifecycle. Every mutation is: governance-gated -> audited
(immutable) -> lineage-extended -> version-bumped -> registry-synced.

A **Plan** is an intent structure — it never executes. The transition into READY (and
the other governed transitions) requires a **policy decision**: the service calls an
injected ``policy_decider`` (the V4-P2 policy engine, wired by the integration
layer). If none is injected, governed transitions require an explicit caller
``approved=True``. **Every plan must derive from an approved goal**: ``create_plan``
requires a source goal whose lineage node is supplied and whose approval is asserted
by the caller (the goal service owns goal approval). Shares the platform's single
``ml.lineage.LineageTracker`` and the shared ``ImmutableAuditLog`` — no parallel
lineage/audit/governance.
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence

from ml.lineage import LineageTracker  # allowed: backend -> ml

from .version import DETERMINISTIC_EPOCH
from .identity import mint_plan, mint_relationship
from .taxonomy import validate_category, validate_relation, is_priority, PlanPriority
from .lifecycle import PlanLifecycle, PlanLifecycleState
from .governance import PlanGovernanceGate, PlanGovernanceError
from .registry import PlanRegistry
from .validation import PlanValidator
from .audit import make_plan_audit_log
from .lineage import make_plan_lineage, make_relationship_lineage
from .models.domain import (
    PlanMetadata, PlanGovernanceRecord, PlanConstraintReference, PlanDependency,
    PlanVersion, PlanRegistryRecord, PlanRecord,
)
from .reports import (
    build_plan_summary_report, build_plan_registry_report, build_plan_lifecycle_report,
    build_plan_dependency_report, build_plan_governance_report, build_plan_validation_report,
    build_plan_audit_report, build_plan_lineage_report,
)

# A policy decider takes (hook, plan) and returns (approved, decision, policy_id, authority).
PolicyDecider = Callable[[str, PlanRecord], tuple]


class PlanDerivationError(RuntimeError):
    """Raised when a plan is derived from a goal that is not approved/ready/active."""



# goal states from which a plan may be derived (an approved/ready goal authorizes
# planning; "active" is accepted because activation supersedes approval).
_DERIVABLE_GOAL_STATES = frozenset({"approved", "active", "completed"})


class PlanService:
    """Stateful service: plan registry, shared lineage tracker, immutable audit log."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[PlanRegistry] = None,
                 policy_decider: Optional[PolicyDecider] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or PlanRegistry()
        self.audit = make_plan_audit_log()
        self.lifecycle = PlanLifecycle()
        self.gate = PlanGovernanceGate()
        self.validator = PlanValidator()
        self.policy_decider = policy_decider

    # --- create (derive from an approved goal) -------------------------------
    def create_plan(self, *, category: str, plan_key: str, metadata: PlanMetadata,
                    source_goal_id: str, source_goal_lineage_id: str, source_goal_state: str,
                    priority: str = PlanPriority.MEDIUM, dependencies: Sequence[str] = (),
                    extra_parents: Sequence[str] = (), owner: str = "plan-ops",
                    created_at: str = DETERMINISTIC_EPOCH) -> PlanRecord:
        """Derive a PROPOSED plan from an approved goal (governance-gated, lineage-rooted).

        Every plan must derive from an approved goal — the caller supplies the source
        goal id, its lineage node, and its lifecycle state (owned by the goal service).
        """
        validate_category(category)
        if not is_priority(priority):
            raise ValueError(f"invalid plan priority {priority!r}")
        if source_goal_state not in _DERIVABLE_GOAL_STATES:
            raise PlanDerivationError(
                f"cannot derive a plan from goal {source_goal_id} in state "
                f"{source_goal_state!r} (must be approved/active/completed)")
        ident = mint_plan(category, source_goal_id, plan_key)
        plan = PlanRecord(
            plan_id=ident.id, category=category, source_goal_id=source_goal_id, plan_key=plan_key,
            metadata=metadata, priority=priority, state=PlanLifecycleState.PROPOSED,
            governance=PlanGovernanceRecord(), dependencies=tuple(dependencies), owner=owner,
            created_at=created_at)

        # parents: the source goal's lineage node (so the plan traces to the patient)
        # plus any explicit extra parents and dependency plans' lineage nodes.
        parents = [source_goal_lineage_id] + list(extra_parents)
        for dep in dependencies:
            if self.registry.exists(dep):
                parents.append(self.registry.get(dep).lineage_id)
        report = self.gate.evaluate(plan=plan, parents=tuple(parents), requires_lineage=True)
        self.gate.raise_if_failed(report)

        node = self.lineage.record(make_plan_lineage(
            plan.plan_id, parents=parents, category=category, reason="created",
            created_at=created_at))
        self.audit.append("plan_created",
                          {"plan_id": plan.plan_id, "category": category,
                           "source_goal_id": source_goal_id, "lineage_id": node.lineage_id,
                           "n_parents": len(parents)}, created_at=created_at)
        plan.lineage_id = node.lineage_id
        # record the source goal as a governed reference
        self.audit.append("plan_goal_linked",
                          {"plan_id": plan.plan_id, "goal_id": source_goal_id},
                          created_at=created_at)
        self._finalize(plan, reason="created", created_at=created_at)
        return plan

    # --- attach a constraint reference (Plan<->Policy) -----------------------
    def attach_constraint(self, plan: PlanRecord, constraint: PlanConstraintReference,
                          created_at: str = DETERMINISTIC_EPOCH) -> PlanRecord:
        plan.constraints = plan.constraints + (constraint,)
        plan.governance = plan.governance.with_constraint(constraint.constraint_id)
        self.audit.append("plan_constraint_attached",
                          {"plan_id": plan.plan_id, "constraint_id": constraint.constraint_id,
                           "hook": constraint.hook}, created_at=created_at)
        self._finalize(plan, reason=f"attach_constraint:{constraint.constraint_id}",
                       created_at=created_at)
        return plan

    # --- dependencies / relationships ----------------------------------------
    def relate(self, plan: PlanRecord, *, relation: str, target_id: str, target_kind: str,
               target_lineage_id: Optional[str] = None,
               created_at: str = DETERMINISTIC_EPOCH) -> PlanDependency:
        """Create a versioned dependency Plan -> target (lineage-tracked)."""
        validate_relation(relation, target_kind)
        dep_id = mint_relationship(plan.plan_id, relation, target_id)
        parents = [plan.lineage_id] + ([target_lineage_id] if target_lineage_id else [])
        node = self.lineage.record(make_relationship_lineage(
            dep_id, parents=parents, relation=relation, created_at=created_at))
        self.audit.append("plan_dependency_added",
                          {"dependency_id": dep_id, "plan_id": plan.plan_id,
                           "relation": relation, "target_id": target_id,
                           "target_kind": target_kind, "lineage_id": node.lineage_id},
                          created_at=created_at)
        version = PlanVersion.compute(f"dep:{dep_id}", None)
        dep = PlanDependency(dependency_id=dep_id, source_plan_id=plan.plan_id,
                             relation=relation, target_id=target_id, target_kind=target_kind,
                             version=version)
        self.registry.register_dependency(dep)
        if relation in ("depends_on", "requires") and target_kind == "plan" \
                and target_id not in plan.dependencies:
            plan.dependencies = plan.dependencies + (target_id,)
            self._finalize(plan, reason=f"relate:{relation}:{target_id}", created_at=created_at)
        return dep



    # --- lifecycle transition (governed) -------------------------------------
    def transition(self, plan: PlanRecord, target: PlanLifecycleState, *, reason: str = "",
                   approved: bool = False, authority: Optional[str] = None,
                   created_at: str = DETERMINISTIC_EPOCH) -> PlanRecord:
        """Move a plan to ``target`` (validated, governed, audited, versioned).

        Governed transitions (APPROVED/READY/SUSPENDED/COMPLETED) require a policy
        decision. If a ``policy_decider`` is injected it is consulted; otherwise the
        caller must pass ``approved=True``. READY additionally fails the gate unless
        approved.
        """
        record = self.lifecycle.transition(plan.state, target, reason=reason,
                                            created_at=created_at)

        decision, policy_id = "n/a", None
        readiness_approved = True
        if self.lifecycle.requires_policy(target):
            hook = self.lifecycle.policy_hook(target)
            if self.policy_decider is not None:
                approved, decision, policy_id, authority = self.policy_decider(hook, plan)
            else:
                decision = "approved" if approved else "denied"
            readiness_approved = approved
            self.audit.append("plan_policy_decision",
                              {"plan_id": plan.plan_id, "hook": hook, "decision": decision,
                               "policy_id": policy_id, "approved": approved},
                              created_at=created_at)
            if not approved:
                plan.governance = plan.governance.with_event(
                    approval_state="rejected", authority=authority, hook=hook,
                    decision=decision, policy_id=policy_id, created_at=created_at)
                self._finalize(plan, reason=f"policy_denied:{hook}", created_at=created_at)
                raise PlanGovernanceError(
                    f"transition {plan.state.value}->{target.value} denied by policy ({hook})")
            plan.governance = plan.governance.with_event(
                approval_state="approved", authority=authority, hook=hook, decision=decision,
                policy_id=policy_id, created_at=created_at)

        report = self.gate.evaluate(plan=plan, parents=(plan.lineage_id,), requires_lineage=True,
                                    target_state=target, readiness_approved=readiness_approved)
        self.gate.raise_if_failed(report)

        self.audit.append("plan_state_change", record.to_dict(), created_at=created_at)
        node = self.lineage.record(make_plan_lineage(
            plan.plan_id, parents=(plan.lineage_id,), category=plan.category,
            reason=f"{record.from_state}->{record.to_state}", created_at=created_at,
            extra={"transition": record.to_dict()}))
        plan.state = target
        plan.lineage_id = node.lineage_id
        self._finalize(plan, reason=f"transition:{record.from_state}->{record.to_state}",
                       created_at=created_at)
        return plan

    # --- validation + reports -------------------------------------------------
    def validate(self, plan: PlanRecord):
        return self.validator.validate(plan=plan, registry=self.registry,
                                       audit_log=self.audit, lineage_tracker=self.lineage)

    def reports(self, plans: Sequence) -> dict:
        plans = list(plans)
        return {
            "plan_summary_report": build_plan_summary_report(plans),
            "plan_registry_report": build_plan_registry_report(self.registry),
            "plan_lifecycle_report": build_plan_lifecycle_report(plans),
            "plan_dependency_report": build_plan_dependency_report(self.registry),
            "plan_governance_report": build_plan_governance_report(plans),
            "plan_audit_report": build_plan_audit_report(self.audit),
            "plan_lineage_report": build_plan_lineage_report(plans, self.lineage),
        }

    def validation_report(self, scope: str, validation_report_dict: dict) -> dict:
        return build_plan_validation_report(scope, validation_report_dict)

    # --- internals ------------------------------------------------------------
    def _finalize(self, plan: PlanRecord, *, reason: str, created_at: str) -> None:
        """Bump the plan version (chained), audit it, then sync the registry."""
        previous = plan.version or None
        new_version = PlanVersion.compute(plan.state_signature(), previous)
        plan.previous_version = previous
        plan.version = new_version
        self.audit.append("plan_version_changed",
                          {"plan_id": plan.plan_id, "version": new_version, "reason": reason},
                          created_at=created_at)
        plan.audit_state = self.audit.head
        self.registry.register(PlanRegistryRecord(
            plan_id=plan.plan_id, category=plan.category, source_goal_id=plan.source_goal_id,
            state=plan.state.value, priority=plan.priority, version=new_version,
            approval_state=plan.governance.approval_state, dependencies=plan.dependencies,
            goal_references=(plan.source_goal_id,),
            policy_references=plan.governance.policy_references, lineage_id=plan.lineage_id,
            audit_state=plan.audit_state, content_signature_value=plan.state_signature()))
        self.audit.append("plan_registered",
                          {"plan_id": plan.plan_id, "version": new_version}, created_at=created_at)
        plan.audit_state = self.audit.head
