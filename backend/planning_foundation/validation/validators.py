"""Plan validation — the eight mandated integrity checks (V4-P3).

``PlanValidator`` verifies a registered plan's integrity across the eight mandated
dimensions: identity, lifecycle, registry, dependency, governance, audit, lineage,
and version. It reuses the shared ``ml.validation.ValidationReport``.
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity, validate_relationship_identity
from ..taxonomy import is_category, is_priority, is_relation
from ..lifecycle import PlanLifecycleState, is_allowed_transition
from ..dependencies import has_cycle
from ..models.domain import PlanRecord, PlanVersion


class PlanValidator:
    """Validates integrity of a registered plan (the eight dimensions)."""

    def validate(self, *, plan: PlanRecord, registry: Any, audit_log: Any,
                 lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()
        pid = plan.plan_id

        # 1. identity integrity
        ident_ok = validate_identity(pid)[0] and is_category(plan.category) \
            and is_priority(plan.priority) and bool(plan.source_goal_id)
        report.add("identity_integrity", ident_ok,
                   f"plan_id={pid} category={plan.category} goal={plan.source_goal_id}")

        # 2. lifecycle integrity — current state is a known state
        report.add("lifecycle_integrity", isinstance(plan.state, PlanLifecycleState),
                   f"state={plan.state.value if isinstance(plan.state, PlanLifecycleState) else plan.state}")

        # 3. registry integrity — registered at this version + lineage
        try:
            rec = registry.get(pid)
            ok = rec.version == plan.version and rec.lineage_id == plan.lineage_id
            report.add("registry_integrity", bool(ok),
                       f"registered version={rec.version} record version={plan.version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        # 4. dependency integrity — well-formed dependencies + no ordering cycle
        try:
            deps = registry.dependencies_for(pid)
            well_formed = all(validate_relationship_identity(d.dependency_id)[0]
                              and is_relation(d.relation) and d.source_plan_id == pid
                              for d in deps)
            acyclic = not has_cycle(_all_dependencies(registry))
            report.add("dependency_integrity", bool(well_formed and acyclic),
                       f"{len(deps)} dependency(ies); acyclic={acyclic}")
        except Exception as exc:
            report.add("dependency_integrity", False, f"error: {exc}")

        # 5. governance integrity — READY plans must be approved
        gov = plan.governance
        gov_ok = (plan.state != PlanLifecycleState.READY) or (gov.approval_state == "approved")
        report.add("governance_integrity", bool(gov_ok),
                   f"approval_state={gov.approval_state} state={plan.state.value}")

        # 6. audit integrity — chain verifies + the plan's head is in the log
        try:
            heads = {e.event_hash for e in audit_log.events()}
            ok = audit_log.verify() and (plan.audit_state in heads)
            report.add("audit_integrity", bool(ok), f"chain_verified={audit_log.verify()}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # 7. lineage integrity — the plan's lineage chain verifies
        try:
            chain_ok = bool(plan.lineage_id) and lineage_tracker.verify_chain(plan.lineage_id)
            report.add("lineage_integrity", bool(chain_ok), f"chain_ok={chain_ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # 8. version integrity — recorded version == recomputed content-addressed version
        try:
            expected = PlanVersion.compute(plan.state_signature(), plan.version_previous())
            report.add("version_integrity", plan.version == expected,
                       f"recorded={plan.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        return report

    @staticmethod
    def can_transition(src: PlanLifecycleState, dst: PlanLifecycleState) -> bool:
        return is_allowed_transition(src, dst)


def _all_dependencies(registry: Any) -> list:
    return [registry.dependency(did) for did in registry.list_dependencies()]
