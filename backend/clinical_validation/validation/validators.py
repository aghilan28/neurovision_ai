"""Clinical-validation content checks (DRP6, build-time).

Validates benchmark / reliability / calibration / evidence integrity, producing structured
``(name, passed, detail)`` results — pure functions, no exceptions.
"""

from __future__ import annotations


class ValidationContentValidator:
    """Build-time validation of the clinical-validation records."""

    def benchmark_integrity(self, benchmark) -> tuple[str, bool, dict]:
        required = {"accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "sensitivity",
                    "specificity", "ece", "brier"}
        dm = benchmark.deterministic_metrics
        ok = required <= set(dm) and all(0.0 <= float(dm[k]) <= 1.0
                                         for k in ("accuracy", "sensitivity", "specificity"))
        return ("benchmark_integrity", bool(ok), {"metrics": sorted(dm)})

    def reliability_integrity(self, reliability) -> tuple[str, bool, dict]:
        ok = 0.0 <= reliability.reliability_score <= 1.0 and len(reliability.failure_modes) > 0
        return ("reliability_integrity", bool(ok),
                {"score": reliability.reliability_score, "repeatable": reliability.repeatable})

    def calibration_integrity(self, calibration) -> tuple[str, bool, dict]:
        ok = (calibration.expected_calibration_error >= 0.0 and calibration.brier >= 0.0
              and "n_bins" in calibration.confidence_distribution)
        return ("calibration_integrity", bool(ok), {"quality": calibration.quality.value})

    def evidence_integrity(self, evidence) -> tuple[str, bool, dict]:
        ok = (bool(evidence.fingerprint) and bool(evidence.benchmark_id)
              and bool(evidence.reliability_id) and bool(evidence.calibration_id)
              and len(evidence.evidence_kinds) >= 4)
        return ("evidence_integrity", bool(ok), {"kinds": list(evidence.evidence_kinds)})

    def content_checks(self, *, benchmark, reliability, calibration, evidence) -> list[tuple]:
        return [
            self.benchmark_integrity(benchmark),
            self.reliability_integrity(reliability),
            self.calibration_integrity(calibration),
            self.evidence_integrity(evidence),
        ]


__all__ = ["ValidationContentValidator"]
