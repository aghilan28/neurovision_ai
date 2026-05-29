"""Inference report builders (reproducible; version/lineage tagged)."""

from __future__ import annotations

from typing import Optional

from ..version import INFERENCE_REPORT_VERSION, OFFLINE_INFERENCE_VERSION


def _header(report_type: str, inference_id: str, lineage_id: str, version_bundle: dict) -> dict:
    return {
        "report_type": report_type,
        "inference_report_version": INFERENCE_REPORT_VERSION,
        "offline_inference_version": OFFLINE_INFERENCE_VERSION,
        "inference_id": inference_id,
        "lineage_id": lineage_id,
        "version_bundle": version_bundle,
    }


def build_inference_report(*, inference_id, lineage_id, version_bundle,
                           prediction, probability, evaluation_metrics, execution) -> dict:
    return {
        **_header("inference", inference_id, lineage_id, version_bundle),
        "n_inference": prediction.get("n"),
        "evaluation_metrics": evaluation_metrics,
        "prediction": prediction,
        "probability_summary": {"calibrated": probability.get("calibrated"),
                                "shape": probability.get("shape")},
        "execution": execution,
    }


def build_calibration_report(*, inference_id, lineage_id, version_bundle, calibration) -> dict:
    return {**_header("calibration", inference_id, lineage_id, version_bundle),
            "calibration": calibration}


def build_coverage_report(*, inference_id, lineage_id, version_bundle, coverage, conformal) -> dict:
    return {**_header("coverage", inference_id, lineage_id, version_bundle),
            "conformal": conformal, "coverage": coverage}


def build_risk_report(*, inference_id, lineage_id, version_bundle, risk) -> dict:
    return {**_header("risk", inference_id, lineage_id, version_bundle), "risk": risk}


def build_summary_report(*, inference_id, lineage_id, version_bundle, summary,
                         evaluation_metrics) -> dict:
    return {**_header("summary", inference_id, lineage_id, version_bundle),
            "summary": summary, "evaluation_metrics": evaluation_metrics}


def build_audit_report(*, inference_id, lineage_id, version_bundle, lineage_chain,
                       execution, validation, inference_record,
                       intelligence: Optional[dict] = None) -> dict:
    return {
        **_header("audit", inference_id, lineage_id, version_bundle),
        "inference_record": inference_record,
        "validation": validation,
        "execution": execution,
        "lineage_chain": lineage_chain,
        "dataset_intelligence_signature": (intelligence or {}).get("signature"),
        "traceable": all(version_bundle.get(k) for k in (
            "dataset_version", "preprocessing_version", "split_version",
            "model_version", "evaluation_version", "calibration_version", "conformal_version")),
    }
