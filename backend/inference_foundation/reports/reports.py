"""Inference report builders (reproducible; version-tagged).

Each report is a plain JSON-able dict, deterministic for a given asset/registry state
(no wall-clock, no randomness). Mirrors the platform report style.
"""

from __future__ import annotations

from typing import Any, Optional

from ..version import INFERENCE_REPORT_VERSION, INFERENCE_FOUNDATION_VERSION


def _header(report_type: str, asset: Any) -> dict:
    return {
        "report_type": report_type,
        "inference_report_version": INFERENCE_REPORT_VERSION,
        "inference_foundation_version": INFERENCE_FOUNDATION_VERSION,
        "prediction_id": asset.prediction_id,
        "model_id": asset.model_id,
        "feature_asset_id": asset.feature_asset_id,
        "case_id": asset.case_id,
        "patient_id": asset.patient_id,
        "prediction_version": asset.version.version,
    }


def build_prediction_report(asset: Any) -> dict:
    return {**_header("prediction", asset), "prediction": asset.prediction.to_dict()}


def build_confidence_report(asset: Any) -> dict:
    return {**_header("confidence", asset), "confidence": asset.confidence.to_dict()}


def build_calibration_report(asset: Any) -> dict:
    return {**_header("calibration", asset), "calibration": asset.calibration.to_dict()}


def build_explainability_report(asset: Any) -> dict:
    return {**_header("explainability", asset), "explanation": asset.explanation.to_dict()}


def build_inference_report(asset: Any) -> dict:
    return {
        **_header("inference", asset),
        "prediction": asset.prediction.to_dict(), "confidence": asset.confidence.to_dict(),
        "calibration": asset.calibration.to_dict(), "explanation_summary":
            asset.explanation.model_attribution_summary,
        "execution_metadata": dict(sorted(asset.execution_metadata.items())),
        "model_metadata": dict(sorted(asset.model_metadata.items())),
        "feature_metadata": dict(sorted(asset.feature_metadata.items())),
        "status": asset.status.value,
    }


def build_audit_report(asset: Any, audit_log: Any) -> dict:
    return {
        **_header("audit", asset), "audit_head": audit_log.head,
        "chain_verified": audit_log.verify(), "n_events": len(audit_log),
        "events": [e.to_dict() for e in audit_log.events()],
    }


def build_lineage_report(asset: Any, lineage_tracker: Any) -> dict:
    chain = lineage_tracker.chain(asset.lineage_id) if asset.lineage_id else []
    return {
        **_header("lineage", asset), "lineage_id": asset.lineage_id,
        "chain_verified": lineage_tracker.verify_chain(asset.lineage_id) if asset.lineage_id else False,
        "chain_length": len(chain), "chain_kinds": [r.kind for r in chain],
        "chain": [r.to_dict() for r in chain],
    }


def build_validation_report(asset: Any, integrity_report: Optional[Any] = None) -> dict:
    out = {**_header("validation", asset), "content_validation": asset.validation.to_dict()}
    if integrity_report is not None:
        out["integrity_validation"] = integrity_report.to_dict()
        out["ok"] = bool(asset.validation.ok and integrity_report.ok)
    else:
        out["ok"] = bool(asset.validation.ok)
    return out


def build_registry_report(registry: Any) -> dict:
    return {
        "report_type": "registry", "inference_report_version": INFERENCE_REPORT_VERSION,
        "inference_foundation_version": INFERENCE_FOUNDATION_VERSION,
        "n_predictions": len(registry.list_predictions()), "registry": registry.to_dict(),
    }
