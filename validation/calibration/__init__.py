"""``validation/calibration`` — calibration & confidence validation (P9-G).

Reads the **existing** calibration/uncertainty evidence the platform already produces —
the P4 model evaluation (ECE + Brier) and the P5 inference asset (confidence score/level,
calibration quality, prediction stability) — and validates it: scores in range, metrics
finite, confidence reported alongside every prediction (NR-4). It reimplements no metric;
it surfaces and checks what the platform computes.
"""

from __future__ import annotations

import math

from ..util import fingerprint
from ..version import VALIDATION_CALIBRATION_VERSION


def _finite(x) -> bool:
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


class CalibrationValidator:
    def run(self, muts: dict, pipeline_result) -> dict:
        checks = []
        per_model = {}
        for arch, mut in sorted(muts.items()):
            cal = mut.evaluation["calibration"]
            unc = mut.evaluation["uncertainty"]
            ece, brier = cal["ece"], cal["brier"]
            ok = (0.0 <= ece <= 1.0) and _finite(brier) and brier >= 0.0
            per_model[arch] = {"ece": ece, "brier": brier,
                               "mean_entropy": unc["mean_entropy"],
                               "mean_confidence": unc["mean_confidence"], "valid": ok}
            checks.append({"name": f"model_calibration:{arch}", "passed": ok,
                           "detail": f"ece={ece:.4f} brier={brier:.4f}"})

        # representative prediction: confidence + calibration are reported alongside label
        conf = pipeline_result.confidence or {}
        cal = pipeline_result.calibration or {}
        confidence_reported = bool(conf.get("confidence_level")) and ("confidence_score" in conf)
        calibration_reported = bool(cal.get("calibration_quality"))
        # prediction stability (P5 fixed-perturbation), surfaced if present
        stability = conf.get("prediction_stability")
        checks.append({"name": "confidence_reported_with_label", "passed": confidence_reported,
                       "detail": f"level={conf.get('confidence_level')} "
                                 f"score={conf.get('confidence_score')}"})
        checks.append({"name": "calibration_reported", "passed": calibration_reported,
                       "detail": f"quality={cal.get('calibration_quality')}"})

        ok = all(c["passed"] for c in checks)
        return {
            "calibration_version": VALIDATION_CALIBRATION_VERSION, "ok": ok,
            "models": per_model,
            "representative_prediction": {
                "confidence_level": conf.get("confidence_level"),
                "confidence_score": conf.get("confidence_score"),
                "calibration_quality": cal.get("calibration_quality"),
                "expected_calibration_error": cal.get("expected_calibration_error"),
                "brier_score": cal.get("brier_score"), "prediction_stability": stability},
            "checks": checks,
            "signature": fingerprint({"models": per_model,
                                      "checks": [(c["name"], c["passed"]) for c in checks]}),
        }


def build_calibration_report(result: dict) -> dict:
    return {"report_type": "calibration", **result}


def build_confidence_report(result: dict) -> dict:
    return {"report_type": "confidence",
            "calibration_version": VALIDATION_CALIBRATION_VERSION,
            "representative_prediction": result.get("representative_prediction"),
            "model_uncertainty": {a: {"mean_entropy": m["mean_entropy"],
                                      "mean_confidence": m["mean_confidence"]}
                                  for a, m in result.get("models", {}).items()}}


__all__ = ["CalibrationValidator", "build_calibration_report", "build_confidence_report"]
