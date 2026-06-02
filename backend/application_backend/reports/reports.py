"""Application report builders (reproducible; version-tagged) (P6-L).

Each report is a plain JSON-able dict, deterministic for a given state (no wall-clock,
no randomness, no secrets). Mirrors the platform report style. The analysis report
reuses the P5 inference report builders (no duplicated result content).
"""

from __future__ import annotations

from typing import Any, Optional

from ..version import APPLICATION_REPORT_VERSION, APPLICATION_BACKEND_VERSION


def _header(report_type: str) -> dict:
    return {
        "report_type": report_type,
        "application_report_version": APPLICATION_REPORT_VERSION,
        "application_backend_version": APPLICATION_BACKEND_VERSION,
    }


def build_user_report(user: Any, audit_log: Any) -> dict:
    return {
        **_header("user"), "user_id": user.user_id, "username": user.username,
        "roles": sorted(r.value for r in user.roles), "status": user.status.value,
        "version": user.version.version, "metadata": dict(sorted(user.metadata.items())),
        "lineage_id": user.lineage_id, "audit_head": user.audit_head,
        "audit_verified": audit_log.verify(), "n_audit_events": len(audit_log),
        "user": user.to_dict(),
    }


def build_session_report(session: Any, audit_log: Any) -> dict:
    return {
        **_header("session"), "session_id": session.session_id, "user_id": session.user_id,
        "status": session.status.value, "version": session.version.version,
        "lineage_id": session.lineage_id, "audit_head": session.audit_head,
        "audit_verified": audit_log.verify(), "n_audit_events": len(audit_log),
        "session": session.to_dict(),
    }


def build_workflow_report(workflow: Any, audit_log: Any) -> dict:
    return {
        **_header("workflow"), "workflow_id": workflow.workflow_id, "upload_id": workflow.upload_id,
        "user_id": workflow.user_id, "stages": [s.value for s in workflow.stages],
        "status": workflow.status.value, "version": workflow.version.version,
        "lineage_id": workflow.lineage_id, "audit_head": workflow.audit_head,
        "audit_verified": audit_log.verify(), "n_audit_events": len(audit_log),
        "workflow": workflow.to_dict(),
    }


def build_analysis_report(analysis: Any, inference_reports: Optional[dict] = None) -> dict:
    out = {
        **_header("analysis"), "analysis_id": analysis.analysis_id,
        "workflow_id": analysis.workflow_id, "prediction_id": analysis.prediction_id,
        "predicted_class": analysis.predicted_class, "predicted_label": analysis.predicted_label,
        "confidence_level": analysis.confidence_level,
        "calibration_quality": analysis.calibration_quality, "status": analysis.status.value,
        "analysis": analysis.to_dict(),
    }
    if inference_reports is not None:
        # Reuse the P5 prediction/confidence/explainability reports (no duplication).
        out["prediction_report"] = inference_reports.get("prediction_report")
        out["confidence_report"] = inference_reports.get("confidence_report")
        out["calibration_report"] = inference_reports.get("calibration_report")
        out["explainability_report"] = inference_reports.get("explainability_report")
    return out


def build_api_report(api_record: Any) -> dict:
    return {**_header("api"), "api": api_record.to_dict(),
            "n_operations": len(api_record.operations)}


def build_registry_report(registry: Any) -> dict:
    return {**_header("registry"), "n_records": len(registry.list_ids()),
            "counts": registry.counts(), "orphans": registry.orphans(),
            "registry": registry.to_dict()}


def build_audit_report(audit_log: Any, *, subject: str) -> dict:
    return {
        **_header("audit"), "subject": subject, "audit_head": audit_log.head,
        "chain_verified": audit_log.verify(), "n_events": len(audit_log),
        "events": [e.to_dict() for e in audit_log.events()],
    }


def build_lineage_report(lineage_tracker: Any, lineage_id: Optional[str]) -> dict:
    chain = lineage_tracker.chain(lineage_id) if lineage_id else []
    return {
        **_header("lineage"), "lineage_id": lineage_id,
        "chain_verified": lineage_tracker.verify_chain(lineage_id) if lineage_id else False,
        "chain_length": len(chain), "chain_kinds": [r.kind for r in chain],
        "chain": [r.to_dict() for r in chain],
    }


def build_validation_report(integrity_report: Any) -> dict:
    return {**_header("validation"), "ok": integrity_report.ok,
            "validation": integrity_report.to_dict()}


__all__ = [
    "build_user_report", "build_session_report", "build_workflow_report", "build_analysis_report",
    "build_api_report", "build_registry_report", "build_audit_report", "build_lineage_report",
    "build_validation_report",
]
