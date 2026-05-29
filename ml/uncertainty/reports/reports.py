"""Uncertainty report builders (reproducible, version/lineage tagged).

Each builder returns a plain dict. The orchestrator persists them via the artifact
store (canonical JSON => deterministic bytes => reproducible checksums).
"""

from __future__ import annotations

from typing import Optional

from ..version import UNCERTAINTY_LAYER_VERSION
from ..schemas import (
    CalibrationResult,
    ConformalResult,
    CoverageResult,
    RiskResult,
    ReliabilityArtifacts,
)


def _header(report_type: str, model_version: str, lineage_id: str, version_bundle: dict) -> dict:
    return {
        "report_type": report_type,
        "uncertainty_layer_version": UNCERTAINTY_LAYER_VERSION,
        "model_version": model_version,
        "lineage_id": lineage_id,
        "version_bundle": version_bundle,
    }


def build_calibration_report(*, calibration: CalibrationResult, reliability: ReliabilityArtifacts,
                             model_version: str, lineage_id: str, version_bundle: dict) -> dict:
    return {
        **_header("calibration", model_version, lineage_id, version_bundle),
        "calibration": calibration.to_dict(),
        "reliability": reliability.to_dict(),
    }


def build_conformal_report(*, conformal: ConformalResult,
                           model_version: str, lineage_id: str, version_bundle: dict) -> dict:
    return {
        **_header("conformal", model_version, lineage_id, version_bundle),
        "conformal": conformal.to_dict(),
    }


def build_coverage_report(*, coverage: CoverageResult,
                          model_version: str, lineage_id: str, version_bundle: dict) -> dict:
    return {
        **_header("coverage", model_version, lineage_id, version_bundle),
        "coverage": coverage.to_dict(),
    }


def build_risk_report(*, risk: RiskResult,
                      model_version: str, lineage_id: str, version_bundle: dict) -> dict:
    return {
        **_header("risk", model_version, lineage_id, version_bundle),
        "risk": risk.to_dict(),
    }


def build_summary_report(*, calibration: CalibrationResult, conformal: ConformalResult,
                         coverage: CoverageResult, risk: RiskResult,
                         model_name: str, model_version: str, lineage_id: str,
                         version_bundle: dict, evaluation_audit: Optional[dict] = None) -> dict:
    return {
        **_header("uncertainty_summary", model_version, lineage_id, version_bundle),
        "model_name": model_name,
        "headline": {
            "temperature": round(calibration.temperature, 6),
            "ece_post": round(calibration.post_ece, 6),
            "target_coverage": round(conformal.target_coverage, 6),
            "observed_coverage": round(coverage.observed_coverage, 6),
            "coverage_reliable": coverage.reliable,
            "mean_set_size": round(float(conformal.set_sizes().mean()), 6),
            "abstain_rate": round(float(risk.abstain_rate), 6),
        },
        "calibration": calibration.to_dict(),
        "conformal": conformal.to_dict(),
        "coverage": coverage.to_dict(),
        "risk": risk.to_dict(),
        "evaluation_audit": evaluation_audit,
    }


def build_audit_report(*, model_version: str, lineage_id: str, version_bundle: dict,
                       lineage_chain: list, uncertainty_record: dict,
                       validation_report: dict, evaluation_audit: Optional[dict] = None) -> dict:
    """The auditability report: lineage chain + versions + validation + eval audit."""
    return {
        **_header("uncertainty_audit", model_version, lineage_id, version_bundle),
        "uncertainty_record": uncertainty_record,
        "validation": validation_report,
        "evaluation_audit": evaluation_audit,
        "lineage_chain": lineage_chain,
        "traceable": all(
            version_bundle.get(k) for k in ("dataset_version", "preprocessing_version",
                                            "split_version", "model_version")
        ),
    }
