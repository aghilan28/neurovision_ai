"""Task validation — the eight mandated integrity checks (V4-P4).

``TaskValidator`` verifies a registered task's integrity across the eight mandated
dimensions: identity, lifecycle, registry, dependency, governance, audit, lineage,
and version. It reuses the shared ``ml.validation.ValidationReport``.
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity, validate_relationship_identity
from ..taxonomy import is_category, is_priority, is_relation
from ..lifecycle import TaskLifecycleState, is_allowed_transition
from ..dependencies import has_cycle
from ..models.domain import TaskRecord, TaskVersion


class TaskValidator:
    """Validates integrity of a registered task (the eight dimensions)."""

    def validate(self, *, task: TaskRecord, registry: Any, audit_log: Any,
                 lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()
        tid = task.task_id

        # 1. identity integrity
        ident_ok = validate_identity(tid)[0] and is_category(task.category) \
            and is_priority(task.priority) and bool(task.source_plan_id)
        report.add("identity_integrity", ident_ok,
                   f"task_id={tid} category={task.category} plan={task.source_plan_id}")

        # 2. lifecycle integrity — current state is a known state
        report.add("lifecycle_integrity", isinstance(task.state, TaskLifecycleState),
                   f"state={task.state.value if isinstance(task.state, TaskLifecycleState) else task.state}")

        # 3. registry integrity — registered at this version + lineage
        try:
            rec = registry.get(tid)
            ok = rec.version == task.version and rec.lineage_id == task.lineage_id
            report.add("registry_integrity", bool(ok),
                       f"registered version={rec.version} record version={task.version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        # 4. dependency integrity — well-formed dependencies + no ordering cycle
        try:
            deps = registry.dependencies_for(tid)
            well_formed = all(validate_relationship_identity(d.dependency_id)[0]
                              and is_relation(d.relation) and d.source_task_id == tid
                              for d in deps)
            acyclic = not has_cycle(_all_dependencies(registry))
            report.add("dependency_integrity", bool(well_formed and acyclic),
                       f"{len(deps)} dependency(ies); acyclic={acyclic}")
        except Exception as exc:
            report.add("dependency_integrity", False, f"error: {exc}")

        # 5. governance integrity — READY tasks must be approved
        gov = task.governance
        gov_ok = (task.state != TaskLifecycleState.READY) or (gov.approval_state == "approved")
        report.add("governance_integrity", bool(gov_ok),
                   f"approval_state={gov.approval_state} state={task.state.value}")

        # 6. audit integrity — chain verifies + the task's head is in the log
        try:
            heads = {e.event_hash for e in audit_log.events()}
            ok = audit_log.verify() and (task.audit_state in heads)
            report.add("audit_integrity", bool(ok), f"chain_verified={audit_log.verify()}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # 7. lineage integrity — the task's lineage chain verifies
        try:
            chain_ok = bool(task.lineage_id) and lineage_tracker.verify_chain(task.lineage_id)
            report.add("lineage_integrity", bool(chain_ok), f"chain_ok={chain_ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # 8. version integrity — recorded version == recomputed content-addressed version
        try:
            expected = TaskVersion.compute(task.state_signature(), task.version_previous())
            report.add("version_integrity", task.version == expected,
                       f"recorded={task.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        return report

    @staticmethod
    def can_transition(src: TaskLifecycleState, dst: TaskLifecycleState) -> bool:
        return is_allowed_transition(src, dst)


def _all_dependencies(registry: Any) -> list:
    return [registry.dependency(did) for did in registry.list_dependencies()]
