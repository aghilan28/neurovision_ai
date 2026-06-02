"""Application *integrity* validation (P6-K, post-build).

Reuses ``ml.validation.ValidationReport`` to produce the eight mandated checks over a
finalized workflow + its session/user/registry/audit/lineage: authentication, session,
workflow, api, registry, audit, lineage, and version integrity. Mirrors the platform
integrity-validation pattern (NR-6).
"""

from __future__ import annotations

from typing import Any, Optional

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity
from ..models.domain import (
    ApiOperation, BackendVersion, EntityKind, SessionStatus, UserStatus, WorkflowStage,
    WorkflowStatus,
)

_REQUIRED_CHAIN_KINDS = {
    "user", "upload", "workflow", "eeg", "processed_eeg", "feature", "model", "prediction",
}
_FULL_STAGES = (
    WorkflowStage.UPLOAD, WorkflowStage.VALIDATE, WorkflowStage.PROCESS, WorkflowStage.FEATURES,
    WorkflowStage.PREDICT, WorkflowStage.CONFIDENCE, WorkflowStage.EXPLANATION,
)


class ApplicationIntegrityValidator:
    """Runs the mandated application-integrity checks over one workflow."""

    def validate(self, *, workflow: Any, user: Any, session: Any, workflow_audit_log: Any,
                 registry: Any, lineage_tracker: Any, api_record: Any,
                 session_audit_log: Optional[Any] = None) -> ValidationReport:
        report = ValidationReport()

        # 1. authentication integrity --------------------------------------------------
        try:
            ok = (user is not None and user.status == UserStatus.ACTIVE
                  and user.user_id == workflow.user_id
                  and (session is None or session.user_id == user.user_id))
            report.add("authentication_integrity", bool(ok),
                       f"user={getattr(user, 'user_id', None)} active={getattr(user, 'status', None)}")
        except Exception as exc:  # pragma: no cover - defensive
            report.add("authentication_integrity", False, f"error: {exc}")

        # 2. session integrity ---------------------------------------------------------
        try:
            if session is None:
                report.add("session_integrity", True, "no session in scope")
            else:
                chain_ok = (session_audit_log.verify() and session.audit_head == session_audit_log.head
                            if session_audit_log is not None else True)
                expected = BackendVersion.compute(session.state_signature(), session.version.previous)
                ok = (session.status in (SessionStatus.ACTIVE, SessionStatus.REVOKED)
                      and session.version.version == expected and chain_ok
                      and validate_identity(session.session_id, "session")[0])
                report.add("session_integrity", bool(ok), f"status={session.status.value}")
        except Exception as exc:
            report.add("session_integrity", False, f"error: {exc}")

        # 3. workflow integrity --------------------------------------------------------
        try:
            ok = (workflow.status == WorkflowStatus.COMPLETED and workflow.stages == _FULL_STAGES
                  and all(workflow.dependencies) and validate_identity(workflow.workflow_id, "workflow")[0]
                  and validate_identity(workflow.prediction_id, "prediction")[0])
            report.add("workflow_integrity", bool(ok),
                       f"stages={[s.value for s in workflow.stages]} status={workflow.status.value}")
        except Exception as exc:
            report.add("workflow_integrity", False, f"error: {exc}")

        # 4. api integrity -------------------------------------------------------------
        try:
            ops = set(api_record.operations)
            ok = (ops == set(ApiOperation) and api_record.api_version == "v1"
                  and validate_identity(api_record.api_id, "api")[0])
            report.add("api_integrity", bool(ok),
                       f"n_operations={len(ops)} version={api_record.api_version}")
        except Exception as exc:
            report.add("api_integrity", False, f"error: {exc}")

        # 5. registry integrity --------------------------------------------------------
        try:
            wf = registry.get(workflow.workflow_id)
            ok = (registry.exists(workflow.workflow_id) and wf.lineage_id == workflow.lineage_id
                  and wf.version == workflow.version.version
                  and wf.entity_kind == EntityKind.WORKFLOW and not registry.orphans())
            report.add("registry_integrity", bool(ok),
                       f"registered={wf.version} orphans={len(registry.orphans())}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        # 6. audit integrity -----------------------------------------------------------
        try:
            ok = workflow_audit_log.verify() and workflow.audit_head == workflow_audit_log.head
            report.add("audit_integrity", bool(ok),
                       f"chain_verified={workflow_audit_log.verify()} "
                       f"head_match={workflow.audit_head == workflow_audit_log.head}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # 7. lineage integrity (chain reaches the patient + the user) -----------------
        try:
            chain_ok = bool(workflow.lineage_id) and lineage_tracker.verify_chain(workflow.lineage_id)
            kinds = ({r.kind for r in lineage_tracker.chain(workflow.lineage_id)}
                     if workflow.lineage_id else set())
            reaches = _REQUIRED_CHAIN_KINDS <= kinds and {"case", "patient"} <= kinds
            report.add("lineage_integrity", bool(chain_ok and reaches),
                       f"chain_ok={chain_ok} kinds={sorted(kinds)}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # 8. version integrity ---------------------------------------------------------
        try:
            expected = BackendVersion.compute(workflow.state_signature(), workflow.version.previous)
            report.add("version_integrity", workflow.version.version == expected,
                       f"recorded={workflow.version.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        return report


__all__ = ["ApplicationIntegrityValidator"]
