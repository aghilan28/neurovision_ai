"""Goal validation — the eight mandated integrity checks (V4-P1).

``GoalValidator`` verifies a registered goal's integrity across the eight mandated
dimensions: identity, lifecycle, registry, relationship, governance, audit, lineage,
and version. It reuses the shared ``ml.validation.ValidationReport``.
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity, validate_relationship_identity
from ..taxonomy import is_category, is_priority, is_relation
from ..lifecycle import GoalLifecycleState, is_allowed_transition
from ..models.domain import GoalRecord, GoalVersion


class GoalValidator:
    """Validates integrity of a registered goal (the eight dimensions)."""

    def validate(self, *, goal: GoalRecord, registry: Any, audit_log: Any,
                 lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()
        gid = goal.goal_id

        # 1. identity integrity
        ident_ok = validate_identity(gid)[0] and is_category(goal.category) \
            and is_priority(goal.priority)
        report.add("identity_integrity", ident_ok, f"goal_id={gid} category={goal.category}")

        # 2. lifecycle integrity — current state is a known state
        report.add("lifecycle_integrity", isinstance(goal.state, GoalLifecycleState),
                   f"state={goal.state.value if isinstance(goal.state, GoalLifecycleState) else goal.state}")

        # 3. registry integrity — registered at this version + lineage
        try:
            rec = registry.get(gid)
            ok = rec.version == goal.version and rec.lineage_id == goal.lineage_id
            report.add("registry_integrity", bool(ok),
                       f"registered version={rec.version} record version={goal.version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        # 4. relationship integrity — every relationship for this goal is well-formed
        try:
            rels = registry.relationships_for(gid)
            rel_ok = all(validate_relationship_identity(r.relationship_id)[0]
                         and is_relation(r.relation) and r.source_goal_id == gid for r in rels)
            report.add("relationship_integrity", bool(rel_ok), f"{len(rels)} relationship(s)")
        except Exception as exc:
            report.add("relationship_integrity", False, f"error: {exc}")

        # 5. governance integrity — ACTIVE goals must be approved
        gov = goal.governance
        gov_ok = (goal.state != GoalLifecycleState.ACTIVE) or (gov.approval_state == "approved")
        report.add("governance_integrity", bool(gov_ok),
                   f"approval_state={gov.approval_state} state={goal.state.value}")

        # 6. audit integrity — chain verifies + the goal's head is in the log
        try:
            heads = {e.event_hash for e in audit_log.events()}
            ok = audit_log.verify() and (goal.audit_state in heads)
            report.add("audit_integrity", bool(ok), f"chain_verified={audit_log.verify()}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # 7. lineage integrity — the goal's lineage chain verifies
        try:
            chain_ok = bool(goal.lineage_id) and lineage_tracker.verify_chain(goal.lineage_id)
            report.add("lineage_integrity", bool(chain_ok), f"chain_ok={chain_ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # 8. version integrity — recorded version == recomputed content-addressed version
        try:
            expected = GoalVersion.compute(goal.state_signature(), goal.version_previous())
            report.add("version_integrity", goal.version == expected,
                       f"recorded={goal.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        return report

    @staticmethod
    def can_transition(src: GoalLifecycleState, dst: GoalLifecycleState) -> bool:
        return is_allowed_transition(src, dst)
