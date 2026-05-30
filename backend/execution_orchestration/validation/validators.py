"""Execution validation — the nine mandated integrity checks (V4-P6).

``ExecutionValidator`` verifies a registered execution's integrity across the nine
mandated dimensions: identity, lifecycle, authorization, assignment, registry,
governance, audit, lineage, and version. Reuses the shared
``ml.validation.ValidationReport``.
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity
from ..lifecycle import ExecutionLifecycleState, is_allowed_transition
from ..coordination import context_complete, assignment_consistent
from ..models.domain import ExecutionRecord, ExecutionVersion


class ExecutionValidator:
    """Validates integrity of a registered execution (the nine dimensions)."""

    def validate(self, *, execution: ExecutionRecord, registry: Any, audit_log: Any,
                 lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()
        eid = execution.execution_id

        # 1. identity integrity
        ident_ok = validate_identity(eid)[0] and bool(execution.source_task_id) \
            and bool(execution.assignment_id)
        report.add("identity_integrity", ident_ok,
                   f"execution_id={eid} task={execution.source_task_id}")

        # 2. lifecycle integrity — current state is a known state
        report.add("lifecycle_integrity", isinstance(execution.state, ExecutionLifecycleState),
                   f"state={execution.state.value if isinstance(execution.state, ExecutionLifecycleState) else execution.state}")

        # 3. authorization integrity — ACTIVE executions must be authorized
        gov = execution.governance
        auth_ok = (execution.state != ExecutionLifecycleState.ACTIVE) \
            or (gov.authorization_state == "authorized")
        report.add("authorization_integrity", bool(auth_ok),
                   f"authorization_state={gov.authorization_state} state={execution.state.value}")

        # 4. assignment integrity — references an assignment consistent with the context
        complete, missing = context_complete(execution.context)
        consistent, why = assignment_consistent(execution.context, execution.assignment)
        report.add("assignment_integrity", bool(complete and consistent),
                   f"context_complete={complete} consistent={consistent} ({why}); missing={missing}")

        # 5. registry integrity — registered at this version + lineage
        try:
            rec = registry.get(eid)
            ok = rec.version == execution.version and rec.lineage_id == execution.lineage_id
            report.add("registry_integrity", bool(ok),
                       f"registered version={rec.version} record version={execution.version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        # 6. governance integrity — ACTIVE requires authorized; no bypass
        report.add("governance_integrity", bool(auth_ok),
                   f"authorization_state={gov.authorization_state}")

        # 7. audit integrity — chain verifies + the execution's head is in the log
        try:
            heads = {e.event_hash for e in audit_log.events()}
            ok = audit_log.verify() and (execution.audit_state in heads)
            report.add("audit_integrity", bool(ok), f"chain_verified={audit_log.verify()}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # 8. lineage integrity — the execution's lineage chain verifies
        try:
            chain_ok = bool(execution.lineage_id) \
                and lineage_tracker.verify_chain(execution.lineage_id)
            report.add("lineage_integrity", bool(chain_ok), f"chain_ok={chain_ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # 9. version integrity — recorded version == recomputed content-addressed version
        try:
            expected = ExecutionVersion.compute(execution.state_signature(),
                                                execution.version_previous())
            report.add("version_integrity", execution.version == expected,
                       f"recorded={execution.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        return report

    @staticmethod
    def can_transition(src: ExecutionLifecycleState, dst: ExecutionLifecycleState) -> bool:
        return is_allowed_transition(src, dst)
