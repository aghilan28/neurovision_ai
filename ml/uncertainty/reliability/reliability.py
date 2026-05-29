"""Reliability analysis: diagrams, tables, histograms and profiles (as data).

All artifacts are deterministic, JSON-able structures derived from calibrated
probabilities (+ optional risk scores). They make the confidence layer inspectable
and auditable rather than a black box.
"""

from __future__ import annotations

import numpy as np

from .._math import reliability_bins
from ..schemas import ReliabilityArtifacts


class ReliabilityAnalyzer:
    def __init__(self, n_bins: int = 15, n_confidence_bins: int = 20):
        self.n_bins = n_bins
        self.n_confidence_bins = n_confidence_bins

    def analyze(
        self,
        *,
        calibrated_probs: np.ndarray,
        labels: np.ndarray,
        class_names: tuple[str, ...],
        risk_scores: np.ndarray | None = None,
        risk_bands: np.ndarray | None = None,
    ) -> ReliabilityArtifacts:
        probs = np.asarray(calibrated_probs, dtype=np.float64)
        y = np.asarray(labels, dtype=int)
        conf = probs.max(axis=1)
        pred = probs.argmax(axis=1)

        # reliability diagram (bins of confidence vs accuracy)
        _, _, bins = reliability_bins(probs, y, self.n_bins)
        reliability_diagram = bins

        # calibration table (same bins, tabular)
        calibration_table = [
            {
                "bin": i,
                "confidence_range": [b["lo"], b["hi"]],
                "count": b["count"],
                "avg_confidence": b["confidence"],
                "accuracy": b["accuracy"],
                "gap": b["gap"],
            }
            for i, b in enumerate(bins)
        ]

        # confidence histogram
        edges = np.linspace(0.0, 1.0, self.n_confidence_bins + 1)
        hist, _ = np.histogram(conf, bins=edges)
        confidence_histogram = {
            "edges": [round(float(e), 4) for e in edges],
            "counts": [int(c) for c in hist],
            "mean_confidence": round(float(conf.mean()), 6) if conf.size else 0.0,
            "median_confidence": round(float(np.median(conf)), 6) if conf.size else 0.0,
        }

        # per-class predicted-confidence profiles
        prediction_confidence_profiles: dict[str, dict] = {}
        for c, name in enumerate(class_names):
            mask = pred == c
            cnt = int(mask.sum())
            prediction_confidence_profiles[name] = {
                "n_predicted": cnt,
                "mean_confidence": round(float(conf[mask].mean()), 6) if cnt else None,
                "min_confidence": round(float(conf[mask].min()), 6) if cnt else None,
                "max_confidence": round(float(conf[mask].max()), 6) if cnt else None,
            }

        # risk profiles (distribution by band + per-class) if risk provided
        risk_profiles: dict = {}
        if risk_scores is not None:
            rs = np.asarray(risk_scores, dtype=np.float64)
            risk_profiles["overall"] = {
                "mean_risk": round(float(rs.mean()), 6) if rs.size else 0.0,
                "p90_risk": round(float(np.quantile(rs, 0.9)), 6) if rs.size else 0.0,
                "max_risk": round(float(rs.max()), 6) if rs.size else 0.0,
            }
            if risk_bands is not None:
                unique, counts = np.unique(np.asarray(risk_bands), return_counts=True)
                risk_profiles["band_distribution"] = {
                    str(u): int(c) for u, c in zip(unique, counts)
                }

        return ReliabilityArtifacts(
            reliability_diagram=reliability_diagram,
            calibration_table=calibration_table,
            confidence_histogram=confidence_histogram,
            prediction_confidence_profiles=prediction_confidence_profiles,
            risk_profiles=risk_profiles,
        )
