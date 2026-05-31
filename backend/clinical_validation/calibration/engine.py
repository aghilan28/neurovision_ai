"""Clinical calibration program (DRP6-D).

Generates deterministic calibration evidence — calibration error (ECE) + Brier, a quality
band, a confidence distribution, and a reliability curve — by **reusing** the DRP-2 benchmark
calibration metrics + the DRP-2 evaluation's binned reliability analysis (confidence vs
accuracy). No retraining; structured, traceable, versioned.
"""

from __future__ import annotations

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..identity import mint_identity
from ..models.domain import CalibrationQuality, CalibrationRecord
from ..version import DETERMINISTIC_EPOCH


def _quality(ece: float) -> CalibrationQuality:
    if ece <= 0.1:
        return CalibrationQuality.WELL_CALIBRATED
    if ece <= 0.25:
        return CalibrationQuality.MODERATELY_CALIBRATED
    return CalibrationQuality.POORLY_CALIBRATED


def build_calibration(outcome, *, created_at: str = DETERMINISTIC_EPOCH) -> CalibrationRecord:
    metrics = outcome.benchmark.deterministic_metrics
    ece = float(metrics.get("ece", 0.0))
    brier = float(metrics.get("brier", 0.0))
    rel = outcome.evaluation.reliability_analysis
    bins = rel.get("bins", [])
    reliability_curve = tuple(
        {"lo": round(float(b["lo"]), 9), "hi": round(float(b["hi"]), 9), "count": int(b["count"]),
         "confidence": round(float(b["confidence"]), 9), "accuracy": round(float(b["accuracy"]), 9)}
        for b in bins)
    confidence_distribution = {
        "mean_confidence": round(float(rel.get("mean_confidence", 0.0)), 9),
        "accuracy": round(float(rel.get("accuracy", 0.0)), 9),
        "n_bins": int(rel.get("n_bins", len(bins))),
        "n_nonempty_bins": sum(1 for b in bins if int(b["count"]) > 0),
    }
    calibration_key = hash_obj({"model_id": outcome.model.model_id, "ece": round(ece, 9),
                                "brier": round(brier, 9),
                                "curve": [dict(sorted(b.items())) for b in reliability_curve]})
    return CalibrationRecord(
        calibration_id=mint_identity("validation_calibration", {
            "model_id": outcome.model.model_id, "calibration_key": calibration_key}).id,
        model_id=outcome.model.model_id, expected_calibration_error=ece, brier=brier,
        quality=_quality(ece), confidence_distribution=confidence_distribution,
        reliability_curve=reliability_curve)


__all__ = ["build_calibration"]
