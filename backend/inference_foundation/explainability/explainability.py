"""Deterministic explainability engine (P5-G).

Generates **structured** (no-image, no-UI) explanations of a prediction:
occlusion-based feature contributions + importance, band importance (model
attribution), channel importance (input-derived salience from the P3 feature asset),
decision factors, and a model-attribution summary. Pure function — deterministic.

Occlusion attribution: each model feature is set to its training mean (its standardized
value -> 0) and the drop in the predicted-class probability is its signed contribution.
"""

from __future__ import annotations

import numpy as np

from ..models.domain import ExplanationMethod, ExplanationRecord, FeatureContribution

_EPS = 1e-12
_TOP_K = 5


class ExplainabilityEngine:
    """Deterministic structured prediction explanations."""

    def explain(self, model, row: np.ndarray, probs: np.ndarray, *,
                feature_names: tuple[str, ...], n_classes: int,
                input_feature_record=None) -> ExplanationRecord:
        probs = np.asarray(probs, dtype=np.float64)
        pred_idx = int(np.argmax(probs))
        base = float(probs[pred_idx])
        mean = np.asarray(getattr(model, "_mean", np.zeros_like(row)), dtype=np.float64)

        contributions = []
        for i, name in enumerate(feature_names):
            occluded = row.copy()
            occluded[i] = mean[i] if i < mean.shape[0] else 0.0
            p = float(np.asarray(model.predict_proba(occluded.reshape(1, -1))[0])[pred_idx])
            contributions.append(FeatureContribution(name=name, contribution=float(base - p)))

        importance = sorted(contributions, key=lambda c: abs(c.contribution), reverse=True)
        total_abs = sum(abs(c.contribution) for c in importance) or 1.0
        importance_norm = tuple(
            FeatureContribution(name=c.name, contribution=abs(c.contribution) / total_abs)
            for c in importance)

        band_importance = self._band_importance(contributions)
        channel_importance = self._channel_importance(input_feature_record)
        decision_factors = tuple({
            "name": c.name, "contribution": round(float(c.contribution), 9),
            "direction": "supports" if c.contribution >= 0 else "opposes"}
            for c in importance[:_TOP_K])
        n_pos = sum(1 for c in contributions if c.contribution > 0)
        n_neg = sum(1 for c in contributions if c.contribution < 0)
        summary = {
            "method": ExplanationMethod.OCCLUSION.value, "predicted_class": pred_idx,
            "architecture": getattr(getattr(model, "architecture", None), "value", "unknown"),
            "top_feature": importance[0].name if importance else None,
            "top_contribution": round(float(importance[0].contribution), 9) if importance else 0.0,
            "n_positive": n_pos, "n_negative": n_neg,
            "sum_abs_contribution": round(float(total_abs), 9),
        }
        return ExplanationRecord(
            method=ExplanationMethod.OCCLUSION, feature_contributions=tuple(contributions),
            feature_importance=importance_norm, band_importance=band_importance,
            channel_importance=channel_importance, decision_factors=decision_factors,
            model_attribution_summary=summary)

    def _band_importance(self, contributions) -> dict:
        """Aggregate model-feature contributions of band_summary.* features by band."""
        out: dict[str, float] = {}
        for c in contributions:
            if c.name.startswith("band_summary."):
                band = c.name.split(".", 1)[1]
                out[band] = out.get(band, 0.0) + abs(c.contribution)
        return dict(sorted(out.items()))

    def _channel_importance(self, input_feature_record) -> dict:
        """Input-derived per-channel salience from the P3 'absolute_power' vector."""
        if input_feature_record is None:
            return {}
        vec = next((v for v in input_feature_record.vectors if v.name == "absolute_power"), None)
        if vec is None or not vec.labels:
            return {}
        vals = np.abs(np.asarray(vec.values, dtype=np.float64))
        total = float(vals.sum()) or 1.0
        return {str(lab): float(v / total) for lab, v in zip(vec.labels, vals)}
