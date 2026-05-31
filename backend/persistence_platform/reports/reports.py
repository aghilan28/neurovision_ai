"""Persistence report builders (DRP4-M; reproducible, version-tagged).

Each report is a plain JSON-able dict, deterministic for a given record/recovery state (no
wall-clock, no randomness). Mirrors the platform report style.
"""

from __future__ import annotations

from typing import Any, Optional

from ..version import PERSISTENCE_REPORT_VERSION, PERSISTENCE_PLATFORM_VERSION


def _header(report_type: str, record: Any) -> dict:
    return {
        "report_type": report_type, "persistence_report_version": PERSISTENCE_REPORT_VERSION,
        "persistence_platform_version": PERSISTENCE_PLATFORM_VERSION,
        "persistence_id": record.persistence_id, "storage_root": record.storage_root,
        "status": record.status.value, "readiness_id": record.readiness_id,
        "persistence_version": record.version.version,
    }


def build_storage_report(record: Any) -> dict:
    return {
        **_header("storage", record),
        "repositories": [r.to_dict() for r in record.repositories],
        "n_objects": (len(record.registry_storage) + len(record.audit_storage)
                      + len(record.execution_storage) + 1),
    }


def build_registry_report(record: Any) -> dict:
    return {**_header("registry", record),
            "registry_storage": [r.to_dict() for r in record.registry_storage]}


def build_audit_persistence_report(record: Any) -> dict:
    return {**_header("audit_persistence", record),
            "audit_storage": [a.to_dict() for a in record.audit_storage]}


def build_lineage_persistence_report(record: Any) -> dict:
    return {**_header("lineage_persistence", record),
            "lineage_storage": record.lineage_storage.to_dict()}


def build_recovery_report(record: Any, recovery: Any) -> dict:
    return {**_header("recovery", record), "recovery": recovery.to_dict()}


def build_validation_report(record: Any, integrity_report: Optional[Any] = None) -> dict:
    out = {**_header("validation", record), "content_validation": record.validation.to_dict()}
    if integrity_report is not None:
        out["integrity_validation"] = integrity_report.to_dict()
        out["ok"] = bool(record.validation.ok and integrity_report.ok)
    else:
        out["ok"] = bool(record.validation.ok)
    return out


def build_readiness_report(record: Any, readiness: Any) -> dict:
    return {**_header("readiness", record), "readiness": readiness.to_dict()}


def build_persistence_summary_report(record: Any, recovery: Any, readiness: Any,
                                     integrity_report: Optional[Any] = None) -> dict:
    out = {
        **_header("summary", record), "readiness_class": record.readiness_class.value,
        "readiness_score": readiness.score, "recovery_status": recovery.status.value,
        "recovery_anchor_verified": recovery.anchor_verified,
        "n_registries": len(record.registry_storage), "n_audit_logs": len(record.audit_storage),
        "n_lineage_nodes": record.lineage_storage.n_nodes,
        "n_execution_streams": len(record.execution_storage),
        "content_validation_ok": record.validation.ok, "record": record.to_dict(),
    }
    if integrity_report is not None:
        out["integrity_validation"] = integrity_report.to_dict()
        out["ok"] = bool(record.validation.ok and integrity_report.ok and recovery.ok)
    else:
        out["ok"] = bool(record.validation.ok and recovery.ok)
    return out


__all__ = [
    "build_storage_report", "build_registry_report", "build_audit_persistence_report",
    "build_lineage_persistence_report", "build_recovery_report", "build_validation_report",
    "build_readiness_report", "build_persistence_summary_report",
]
