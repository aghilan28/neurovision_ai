"""Clinical risk scoring + abstain/escalate decisions.

Risk is derived from calibrated uncertainty so it is honest and explainable (no
black-box scores). For each window:

  * ``risk_score`` combines top-1 uncertainty (1 - calibrated confidence) with the
    conformal set size (ambiguity): larger sets => higher risk.
  * ``band`` discretizes risk into low / medium / high.
  * ``abstain`` is True (escalate to a human) when risk exceeds the abstain
    threshold or the conformal set is ambiguous (size != 1) — consistent with
    decision-support, never autonomy (Scope O5/R1).

A forward ``operational_risk_hook`` is provided as the documented attachment point
for future operational risk signals (kept inert in V1).
"""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np

from ..schemas import RiskResult


class RiskAssessor:
    def __init__(
        self,
        low_threshold: float = 0.2,
        high_threshold: float = 0.5,
        abstain_threshold: float = 0.5,
        size_weight: float = 0.25,
        operational_risk_hook: Optional[Callable[[np.ndarray], np.ndarray]] = None,
    ):
        if not (0.0 <= low_threshold < high_threshold <= 1.0):
            raise ValueError("require 0 <= low_threshold < high_threshold <= 1")
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold
        self.abstain_threshold = abstain_threshold
        self.size_weight = size_weight
        # Future operational risk hook (V2+). Inert in V1 by default.
        self.operational_risk_hook = operational_risk_hook

    def assess(
        self,
        *,
        calibrated_probs: np.ndarray,
        class_names: tuple[str, ...],
        prediction_sets: Optional[np.ndarray] = None,
        labels: Optional[np.ndarray] = None,
    ) -> RiskResult:
        probs = np.asarray(calibrated_probs, dtype=np.float64)
        n, k = probs.shape
        confidence = probs.max(axis=1)
        pred = probs.argmax(axis=1)
        base_risk = 1.0 - confidence

        if prediction_sets is not None:
            sizes = np.asarray(prediction_sets, dtype=bool).sum(axis=1)
            # normalize ambiguity by (k-1); singletons add no ambiguity risk
            ambiguity = np.clip((sizes - 1) / max(1, k - 1), 0.0, 1.0)
            risk = np.clip(base_risk + self.size_weight * ambiguity, 0.0, 1.0)
        else:
            sizes = np.ones(n, dtype=int)
            risk = base_risk

        if self.operational_risk_hook is not None:  # forward hook (inert in V1)
            risk = np.clip(risk + self.operational_risk_hook(risk), 0.0, 1.0)

        bands = np.where(risk >= self.high_threshold, "high",
                         np.where(risk >= self.low_threshold, "medium", "low"))
        abstain = (risk >= self.abstain_threshold)
        if prediction_sets is not None:
            abstain = abstain | (sizes != 1)
        low_conf_alerts = np.nonzero(abstain)[0]

        per_class_risk: dict[str, dict] = {}
        for c, name in enumerate(class_names):
            mask = pred == c
            cnt = int(mask.sum())
            per_class_risk[name] = {
                "n_predicted": cnt,
                "mean_risk": round(float(risk[mask].mean()), 6) if cnt else None,
                "mean_confidence": round(float(confidence[mask].mean()), 6) if cnt else None,
                "abstain_count": int(abstain[mask].sum()) if cnt else 0,
            }

        return RiskResult(
            risk_scores=risk,
            confidence=confidence,
            bands=bands,
            abstain=abstain,
            low_confidence_alerts=low_conf_alerts,
            band_thresholds={
                "low": self.low_threshold,
                "high": self.high_threshold,
                "abstain": self.abstain_threshold,
            },
            per_class_risk=per_class_risk,
            abstain_rate=float(abstain.mean()) if n else 0.0,
        )
