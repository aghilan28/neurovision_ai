"""GoalService — the governed orchestration hub for the Goal Intelligence Foundation.

Ties identity, taxonomy, lifecycle, governance, registry, audit, and lineage into
the use cases that create and evolve a Goal, relate it to other artifacts, and move
it through its lifecycle. Every mutation is: governance-gated -> audited (immutable)
-> lineage-extended -> version-bumped -> registry-synced. Nothing happens outside
this governed path.

A **Goal** is *intent* — it never performs actions. The transition into ACTIVE (and
the other governed transitions) requires a **policy decision**: the service calls an
injected ``policy_decider`` (the V4-P2 policy engine, wired by the integration
layer). If none is injected, governed transitions require an explicit caller
``approved=True`` (so the subsystem is testable in isolation while never silently
self-approving). Shares the platform's single ``ml.lineage.LineageTracker`` and the
shared ``ImmutableAuditLog`` — no parallel lineage/audit/governance.
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence

from ml.lineage import LineageTracker  # allowed: backend -> ml

from .version import DETERMINISTIC_EPOCH
from .identity import mint_goal, mint_relationship
from .taxonomy import validate_category, validate_relation, is_priority, GoalPriority
from .lifecycle import GoalLifecycle, GoalLifecycleState
from .governance import GoalGovernanceGate
from .registry import GoalRegistry
from .validation import GoalValidator
from .audit import make_goal_audit_log
from .lineage import make_goal_lineage, make_relationship_lineage
from .models.domain import (
    GoalMetadata, GoalGovernance, GoalConstraintReference, GoalRelationship,
    GoalVersion, GoalRegistryRecord, GoalRecord,
)
from .reports import (
    build_goal_summary_report, build_goal_registry_report, build_goal_lifecycle_report,
    build_goal_relationship_report, build_goal_governance_report, build_goal_validation_report,
    build_goal_audit_report, build_goal_lineage_report,
)

# A policy decider takes (hook, goal) and returns (approved, decision, policy_id, authority).
PolicyDecider = Callable[[str, GoalRecord], tuple]



class GoalService:
    """Stateful service: goal registry, shared lineage tracker, immutable audit log."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[GoalRegistry] = None,
                 policy_decider: Optional[PolicyDecider] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or GoalRegistry()
        self.audit = make_goal_audit_log()
        self.lifecycle = GoalLifecycle()
        self.gate = GoalGovernanceGate()
        self.validator = GoalValidator()
        self.policy_decider = policy_decider

    # --- create ---------------------------------------------------------------
    def create_goal(self, *, category: str, definition_key: str, metadata: GoalMetadata,
                    priority: str = GoalPriority.MEDIUM, dependencies: Sequence[str] = (),
                    derived_from: Sequence[str] = (), owner: str = "goal-ops",
                    created_at: str = DETERMINISTIC_EPOCH) -> GoalRecord:
        """Create a PROPOSED goal (intent), governance-gated + lineage-rooted."""
        validate_category(category)
        if not is_priority(priority):
            raise ValueError(f"invalid goal priority {priority!r}")
        ident = mint_goal(category, definition_key)
        goal = GoalRecord(
            goal_id=ident.id, category=category, definition_key=definition_key,
            metadata=metadata, priority=priority, state=GoalLifecycleState.PROPOSED,
            governance=GoalGovernance(), dependencies=tuple(dependencies), owner=owner,
            created_at=created_at)

        # parents: the upstream artifacts the intent derives from (+ dependency goals'
        # lineage nodes), so the goal traces back through operational intelligence.
        parents = list(derived_from)
        for dep in dependencies:
            if self.registry.exists(dep):
                parents.append(self.registry.get(dep).lineage_id)
        report = self.gate.evaluate(goal=goal, parents=tuple(parents),
                                    requires_lineage=len(parents) > 0)
        self.gate.raise_if_failed(report)

        node = self.lineage.record(make_goal_lineage(
            goal.goal_id, parents=parents, category=category, reason="created",
            created_at=created_at))
        self.audit.append("goal_created", {"goal_id": goal.goal_id, "category": category,
                                           "lineage_id": node.lineage_id,
                                           "n_parents": len(parents)}, created_at=created_at)
        goal.lineage_id = node.lineage_id
        self._finalize(goal, reason="created", created_at=created_at)
        return goal

    # --- attach a constraint reference (Goal<->Policy) -----------------------
    def attach_constraint(self, goal: GoalRecord, constraint: GoalConstraintReference,
                          created_at: str = DETERMINISTIC_EPOCH) -> GoalRecord:
        goal.constraints = goal.constraints + (constraint,)
        self.audit.append("goal_constraint_attached",
                          {"goal_id": goal.goal_id, "constraint_id": constraint.constraint_id,
                           "hook": constraint.hook}, created_at=created_at)
        self._finalize(goal, reason=f"attach_constraint:{constraint.constraint_id}",
                       created_at=created_at)
        return goal

    # --- relationships --------------------------------------------------------
    def relate(self, goal: GoalRecord, *, relation: str, target_id: str, target_kind: str,
               target_lineage_id: Optional[str] = None,
               created_at: str = DETERMINISTIC_EPOCH) -> GoalRelationship:
        """Create a versioned relationship Goal -> target (lineage-tracked)."""
        validate_relation(relation, target_kind)
        rel_id = mint_relationship(goal.goal_id, relation, target_id)
        parents = [goal.lineage_id] + ([target_lineage_id] if target_lineage_id else [])
        node = self.lineage.record(make_relationship_lineage(
            rel_id, parents=parents, relation=relation, created_at=created_at))
        self.audit.append("goal_relationship_added",
                          {"relationship_id": rel_id, "goal_id": goal.goal_id,
                           "relation": relation, "target_id": target_id,
                           "target_kind": target_kind, "lineage_id": node.lineage_id},
                          created_at=created_at)
        version = GoalVersion.compute(
            {"rel": rel_id}.__repr__(), None)  # deterministic version stamp
        rel = GoalRelationship(relationship_id=rel_id, source_goal_id=goal.goal_id,
                               relation=relation, target_id=target_id, target_kind=target_kind,
                               version=version)
        self.registry.register_relationship(rel)
        # record the dependency on the goal when relation is depends_on/blocked_by
        if relation in ("depends_on", "blocked_by") and target_kind == "goal" \
                and target_id not in goal.dependencies:
            goal.dependencies = goal.dependencies + (target_id,)
            self._finalize(goal, reason=f"relate:{relation}:{target_id}", created_at=created_at)
        return rel



    # --- lifecycle transition (governed) -------------------------------------
    def transition(self, goal: GoalRecord, target: GoalLifecycleState, *, reason: str = "",
                   approved: bool = False, authority: Optional[str] = None,
                   created_at: str = DETERMINISTIC_EPOCH) -> GoalRecord:
        """Move a goal to ``target`` (validated, governed, audited, versioned).

        Governed transitions (APPROVED/ACTIVE/SUSPENDED/COMPLETED) require a policy
        decision. If a ``policy_decider`` is injected it is consulted; otherwise the
        caller must pass ``approved=True``. ACTIVE additionally fails the governance
        gate unless approved.
        """
        record = self.lifecycle.transition(goal.state, target, reason=reason,
                                            created_at=created_at)

        # policy-governed transitions
        decision, policy_id = "n/a", None
        activation_approved = True
        if self.lifecycle.requires_policy(target):
            hook = self.lifecycle.policy_hook(target)
            if self.policy_decider is not None:
                approved, decision, policy_id, authority = self.policy_decider(hook, goal)
            else:
                decision = "approved" if approved else "denied"
            activation_approved = approved
            self.audit.append("goal_policy_decision",
                              {"goal_id": goal.goal_id, "hook": hook, "decision": decision,
                               "policy_id": policy_id, "approved": approved},
                              created_at=created_at)
            if not approved:
                # record governance rejection on the goal and block the transition
                goal.governance = goal.governance.with_event(
                    approval_state="rejected", authority=authority, hook=hook,
                    decision=decision, policy_id=policy_id, created_at=created_at)
                self._finalize(goal, reason=f"policy_denied:{hook}", created_at=created_at)
                from .governance import GoalGovernanceError
                raise GoalGovernanceError(
                    f"transition {goal.state.value}->{target.value} denied by policy ({hook})")
            goal.governance = goal.governance.with_event(
                approval_state="approved", authority=authority, hook=hook, decision=decision,
                policy_id=policy_id, created_at=created_at)

        report = self.gate.evaluate(goal=goal, parents=(goal.lineage_id,), requires_lineage=True,
                                    target_state=target, activation_approved=activation_approved)
        self.gate.raise_if_failed(report)

        self.audit.append("goal_state_change", record.to_dict(), created_at=created_at)
        node = self.lineage.record(make_goal_lineage(
            goal.goal_id, parents=(goal.lineage_id,), category=goal.category,
            reason=f"{record.from_state}->{record.to_state}", created_at=created_at,
            extra={"transition": record.to_dict()}))
        goal.state = target
        goal.lineage_id = node.lineage_id
        self._finalize(goal, reason=f"transition:{record.from_state}->{record.to_state}",
                       created_at=created_at)
        return goal

    # --- validation + reports -------------------------------------------------
    def validate(self, goal: GoalRecord):
        return self.validator.validate(goal=goal, registry=self.registry,
                                       audit_log=self.audit, lineage_tracker=self.lineage)

    def reports(self, goals: Sequence) -> dict:
        goals = list(goals)
        return {
            "goal_summary_report": build_goal_summary_report(goals),
            "goal_registry_report": build_goal_registry_report(self.registry),
            "goal_lifecycle_report": build_goal_lifecycle_report(goals),
            "goal_relationship_report": build_goal_relationship_report(self.registry),
            "goal_governance_report": build_goal_governance_report(goals),
            "goal_audit_report": build_goal_audit_report(self.audit),
            "goal_lineage_report": build_goal_lineage_report(goals, self.lineage),
        }

    def validation_report(self, scope: str, validation_report_dict: dict) -> dict:
        return build_goal_validation_report(scope, validation_report_dict)

    # --- internals ------------------------------------------------------------
    def _finalize(self, goal: GoalRecord, *, reason: str, created_at: str) -> None:
        """Bump the goal version (chained), audit it, then sync the registry."""
        previous = goal.version or None
        new_version = GoalVersion.compute(goal.state_signature(), previous)
        goal.previous_version = previous
        goal.version = new_version
        self.audit.append("goal_version_changed",
                          {"goal_id": goal.goal_id, "version": new_version, "reason": reason},
                          created_at=created_at)
        goal.audit_state = self.audit.head
        self.registry.register(GoalRegistryRecord(
            goal_id=goal.goal_id, category=goal.category, state=goal.state.value,
            priority=goal.priority, version=new_version,
            approval_state=goal.governance.approval_state, dependencies=goal.dependencies,
            constraint_ids=goal.constraint_ids, lineage_id=goal.lineage_id,
            audit_state=goal.audit_state, content_signature_value=goal.state_signature()))
        self.audit.append("goal_registered",
                          {"goal_id": goal.goal_id, "version": new_version}, created_at=created_at)
        goal.audit_state = self.audit.head
