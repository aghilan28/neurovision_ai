"""Inference *integrity* validation (P5-K, post-build).

Reuses ``ml.validation.ValidationReport`` to produce the full nine mandated checks over
a finalized, registered prediction asset: the five content checks (prediction /
confidence / calibration / explanation / determinism — re-affirmed from the asset) plus
the four structural checks (registry, audit, lineage, version). Mirrors the platform
pattern (NR-6).
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity
from ..models.domain import PredictionVersion
from .validators import InferenceContentValidator


class InferenceIntegrityValidator:
    """Runs the mandated inference-asset integrity checks."""

    def __init__(self) -> None:
        self._content = InferenceContentValidator()

    def validate(self, *, asset: Any, registry: Any, audit_log: Any,
                 lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()
        n_classes = len(asset.prediction.classes)
        n_features = len(asset.explanation.feature_contributions)

        name, ok, _ = self._content.prediction_integrity(asset.prediction, n_classes)
        report.add("prediction_integrity", ok, f"n_classes={n_classes}")
        name, ok, _ = self._content.confidence_integrity(asset.confidence)
        report.add("confidence_integrity", ok, f"level={asset.confidence.confidence_level.value}")
        name, ok, _ = self._content.calibration_integrity(asset.calibration)
        report.add("calibration_integrity", ok, f"quality={asset.calibration.calibration_quality.value}")
        name, ok, _ = self._content.explanation_integrity(asset.explanation, n_features)
        report.add("explanation_integrity", ok, f"n_contributions={n_features}")
        det = next((c for c in asset.validation.checks if c[0] == "determinism_integrity"), None)
        report.add("determinism_integrity", bool(det[1]) if det else False,
                   "re-inference reproduces identical prediction fingerprints")

        # --- registry integrity ---
        try:
            rec = registry.get(asset.prediction_id)
            ok = (rec.version == asset.version.version and rec.lineage_id == asset.lineage_id
                  and rec.status == asset.status and rec.model_id == asset.model_id
                  and rec.feature_asset_id == asset.feature_asset_id)
            report.add("registry_integrity", bool(ok),
                       f"registered={rec.version} asset={asset.version.version}")
        except Exception as exc:  # pragma: no cover - defensive
            report.add("registry_integrity", False, f"error: {exc}")

        # --- audit integrity ---
        try:
            ok = audit_log.verify() and asset.audit_head == audit_log.head
            report.add("audit_integrity", bool(ok),
                       f"chain_verified={audit_log.verify()} head_match={asset.audit_head == audit_log.head}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # --- lineage integrity (chain reaches the patient root) ---
        try:
            chain_ok = bool(asset.lineage_id) and lineage_tracker.verify_chain(asset.lineage_id)
            kinds = ({r.kind for r in lineage_tracker.chain(asset.lineage_id)}
                     if asset.lineage_id else set())
            reaches = {"patient", "case", "eeg", "processed_eeg", "feature", "dataset",
                       "training_run", "model", "prediction"} <= kinds
            ids_ok = (validate_identity(asset.prediction_id, "prediction")[0]
                      and validate_identity(asset.model_id, "model")[0]
                      and validate_identity(asset.feature_asset_id, "feature")[0])
            report.add("lineage_integrity", bool(chain_ok and reaches and ids_ok),
                       f"chain_ok={chain_ok} kinds={sorted(kinds)}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # --- version integrity ---
        try:
            expected = PredictionVersion.compute(asset.state_signature(), asset.version.previous)
            report.add("version_integrity", asset.version.version == expected,
                       f"recorded={asset.version.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        return report
