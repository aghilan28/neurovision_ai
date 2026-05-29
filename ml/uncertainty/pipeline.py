"""The deterministic uncertainty pipeline (V1-P6 end to end).

Chains the clinical confidence stages into one reproducible flow that operates on
*logits arrays* (model-agnostic):

  calibration (temperature scaling) → conformal (split conformal) →
  coverage (target vs observed, drift, violations) → risk (scores, bands, abstain)
  → reliability (diagrams/tables/histograms/profiles)

The calibration set and evaluation set must be patient-disjoint (the orchestrator
supplies the patient ids and the pipeline records them for validation). Everything
is deterministic, so the uncertainty outputs are reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .calibration import CalibrationPipeline, TemperatureScaler
from .conformal import SplitConformalPredictor
from .coverage import CoverageTracker
from .risk import RiskAssessor
from .reliability import ReliabilityAnalyzer
from .schemas import CalibrationResult, ConformalResult, CoverageResult, RiskResult, ReliabilityArtifacts


@dataclass
class UncertaintyOutput:
    calibration: CalibrationResult
    conformal: ConformalResult
    coverage: CoverageResult
    risk: RiskResult
    reliability: ReliabilityArtifacts
    calibrated_test_probs: np.ndarray
    temperature: float
    scaler: TemperatureScaler


class UncertaintyPipeline:
    def __init__(
        self,
        alpha: float = 0.1,
        n_bins: int = 15,
        risk_assessor: Optional[RiskAssessor] = None,
        coverage_tolerance: float = 0.05,
    ):
        self.alpha = alpha
        self.calibration = CalibrationPipeline(n_bins=n_bins)
        self.conformal = SplitConformalPredictor(alpha=alpha)
        self.coverage = CoverageTracker(tolerance=coverage_tolerance)
        self.risk = risk_assessor or RiskAssessor()
        self.reliability = ReliabilityAnalyzer(n_bins=n_bins)

    def run(
        self,
        *,
        calib_logits: np.ndarray,
        calib_labels: np.ndarray,
        eval_logits: np.ndarray,
        eval_labels: np.ndarray,
        class_names: tuple[str, ...],
        dataset_version: Optional[str] = None,
        split_version: Optional[str] = None,
    ) -> UncertaintyOutput:
        # 1. calibration (fit on patient-disjoint calibration set)
        cal_result, scaler = self.calibration.calibrate(calib_logits, calib_labels)

        calib_probs = scaler.transform(calib_logits)
        test_probs = scaler.transform(eval_logits)

        # 2. conformal (fit on calibration set, predict on test set)
        self.conformal.fit(calib_probs, calib_labels)
        conformal_result = self.conformal.predict(test_probs, class_names)

        # 3. coverage (assess on patient-disjoint test set)
        coverage_result = self.coverage.assess(
            prediction_sets=conformal_result.prediction_sets,
            labels=eval_labels,
            target_coverage=conformal_result.target_coverage,
            class_names=class_names,
            dataset_version=dataset_version,
            split_version=split_version,
        )

        # 4. risk (per-window risk, bands, abstain)
        risk_result = self.risk.assess(
            calibrated_probs=test_probs,
            class_names=class_names,
            prediction_sets=conformal_result.prediction_sets,
            labels=eval_labels,
        )

        # 5. reliability artifacts
        reliability = self.reliability.analyze(
            calibrated_probs=test_probs,
            labels=eval_labels,
            class_names=class_names,
            risk_scores=risk_result.risk_scores,
            risk_bands=risk_result.bands,
        )

        return UncertaintyOutput(
            calibration=cal_result,
            conformal=conformal_result,
            coverage=coverage_result,
            risk=risk_result,
            reliability=reliability,
            calibrated_test_probs=test_probs,
            temperature=scaler.temperature,
            scaler=scaler,
        )
