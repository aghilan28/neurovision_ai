"""Serving report builders (DRP3-K; reproducible, version-tagged).

Each report is a plain JSON-able dict, deterministic for a given record/registry state
(no wall-clock, no randomness). Mirrors the platform report style.
"""

from __future__ import annotations

from typing import Any, Optional

from ..contracts import (
    CONTRACT_REGISTRY, build_execution_metadata_contract, build_prediction_response_contract,
)
from ..version import SERVING_REPORT_VERSION, SERVING_PLATFORM_VERSION


def _header(report_type: str, execution: Any) -> dict:
    return {
        "report_type": report_type, "serving_report_version": SERVING_REPORT_VERSION,
        "serving_platform_version": SERVING_PLATFORM_VERSION,
        "execution_id": execution.execution_id, "request_id": execution.request_id,
        "response_id": execution.response_id, "model_id": execution.model_id,
        "prediction_id": execution.prediction_id, "status": execution.status.value,
        "execution_version": execution.version.version,
    }


def build_serving_report(execution: Any) -> dict:
    return {**_header("serving", execution), "execution": execution.to_dict()}


def build_execution_report(execution: Any) -> dict:
    return {**_header("execution", execution),
            "lifecycle": execution.lifecycle.to_dict(),
            "execution_metadata": build_execution_metadata_contract(execution)}


def build_validation_report(execution: Any, integrity_report: Optional[Any] = None) -> dict:
    out = {**_header("validation", execution), "content_validation": execution.validation.to_dict()}
    if integrity_report is not None:
        out["integrity_validation"] = integrity_report.to_dict()
        out["ok"] = bool(execution.validation.ok and integrity_report.ok)
    else:
        out["ok"] = bool(execution.validation.ok)
    return out


def build_readiness_report(execution: Any, readiness: Any) -> dict:
    return {**_header("readiness", execution), "readiness": readiness.to_dict()}


def build_registry_report(registry: Any) -> dict:
    return {
        "report_type": "registry", "serving_report_version": SERVING_REPORT_VERSION,
        "serving_platform_version": SERVING_PLATFORM_VERSION, "registry": registry.to_dict(),
    }


def build_audit_report(execution: Any, audit_log: Any) -> dict:
    return {
        **_header("audit", execution), "audit_head": audit_log.head,
        "chain_verified": audit_log.verify(), "n_events": len(audit_log),
        "events": [e.to_dict() for e in audit_log.events()],
    }


def build_lineage_report(execution: Any, lineage_tracker: Any) -> dict:
    chain_id = execution.response.lineage_id or execution.lineage_id
    chain = lineage_tracker.chain(chain_id) if chain_id else []
    return {
        **_header("lineage", execution), "lineage_id": execution.lineage_id,
        "response_lineage_id": execution.response.lineage_id,
        "chain_verified": lineage_tracker.verify_chain(chain_id) if chain_id else False,
        "chain_length": len(chain), "chain_kinds": [r.kind for r in chain],
        "chain": [r.to_dict() for r in chain],
    }


def build_contract_report(execution: Any) -> dict:
    return {
        **_header("contract", execution),
        "registered_contracts": dict(sorted(CONTRACT_REGISTRY.items())),
        "response_contract": build_prediction_response_contract(execution.response),
    }


def build_service_summary_report(execution: Any, readiness: Any,
                                 integrity_report: Optional[Any] = None) -> dict:
    out = {
        **_header("summary", execution), "readiness_class": execution.readiness_class.value,
        "readiness_score": readiness.score, "lifecycle_final_state": execution.lifecycle.final_state,
        "predicted_class": execution.response.predicted_class,
        "confidence_level": execution.response.confidence_level,
        "calibration_quality": execution.response.calibration_quality,
        "content_validation_ok": execution.validation.ok, "execution": execution.to_dict(),
    }
    if integrity_report is not None:
        out["integrity_validation"] = integrity_report.to_dict()
        out["ok"] = bool(execution.validation.ok and integrity_report.ok)
    else:
        out["ok"] = bool(execution.validation.ok)
    return out


__all__ = [
    "build_serving_report", "build_execution_report", "build_validation_report",
    "build_readiness_report", "build_registry_report", "build_audit_report", "build_lineage_report",
    "build_contract_report", "build_service_summary_report",
]
