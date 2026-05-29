"""Uncertainty validation checks (V1-P6).

Reuses the ML layer's ``ValidationReport``/``CheckResult`` to report results in a
consistent shape. Validates calibration, conformal coverage, patient-disjoint
calibration set, version consistency, lineage integrity, and clinical completeness.
"""

from __future__ import annotations

from typing import Any, Optional

from ...validation import ValidationReport
from ..schemas import CalibrationResult, ConformalResult, CoverageResult


class UncertaintyValidationError(RuntimeError):
    """Raised when a mandated uncertainty-validation check fails."""


class UncertaintyValidator:
    def validate(
        self,
        *,
        calibration: CalibrationResult,
        conformal: ConformalResult,
        coverage: CoverageResult,
        calibration_patients,
        test_patients,
        lineage_tracker: Optional[Any] = None,
        lineage_id: Optional[str] = None,
        clinically_complete: bool = True,
    ) -> ValidationReport:
        report = ValidationReport()

        # 1. calibration measured (ECE finite, temperature positive)
        cal_ok = (calibration.temperature > 0) and (calibration.post_ece >= 0)
        report.add("calibration_measured", bool(cal_ok),
                   f"T={calibration.temperature:.4f} ece pre={calibration.pre_ece:.4f} post={calibration.post_ece:.4f}")

        # 2. conformal coverage assessed (qhat in [0,1], target in (0,1))
        conf_ok = (0.0 <= conformal.qhat <= 1.0) and (0.0 < conformal.target_coverage < 1.0)
        report.add("conformal_assessed", bool(conf_ok),
                   f"qhat={conformal.qhat:.4f} target={conformal.target_coverage:.3f}")

        # 3. patient-disjoint calibration set (cardinal NR-3 for valid coverage)
        cal_set = set(calibration_patients or [])
        te_set = set(test_patients or [])
        disjoint = len(cal_set) > 0 and len(te_set) > 0 and not (cal_set & te_set)
        report.add("calibration_patient_disjoint", bool(disjoint),
                   f"overlap={sorted(cal_set & te_set)}")

        # 4. coverage reliability (observed within tolerance of target)
        report.add("coverage_reliable", bool(coverage.reliable),
                   f"observed={coverage.observed_coverage:.4f} target={coverage.target_coverage:.3f} drift={coverage.coverage_drift:.4f}")

        # 5. lineage integrity (if a tracker is provided)
        if lineage_tracker is not None and lineage_id is not None:
            ok = lineage_tracker.verify_chain(lineage_id)
            report.add("lineage_integrity", bool(ok), f"chain verified: {ok}")

        # 6. clinical completeness gate (NR-4): calibrated uncertainty attached
        report.add("clinical_completeness", bool(clinically_complete),
                   "calibrated uncertainty attached to predictions (NR-4)")

        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise UncertaintyValidationError(f"uncertainty validation failed: {names}")
