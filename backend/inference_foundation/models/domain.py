"""Clinical Inference domain entities + closed vocabularies (Productization P5).

Pure data shapes (JSON-able, content-hashable). No I/O, no orchestration, no model
execution — this module owns only the *shapes* and the *closed vocabularies* (no
free-form states). The execution / prediction / confidence / calibration /
explainability engines produce these records; the service assembles the immutable
``InferenceRecord`` (the prediction asset).

Mirrors ``backend.model_foundation.models.domain`` so the inference layer is shaped
exactly like the rest of the platform (NR-6: reuse patterns, don't invent).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    INFERENCE_DOMAIN_VERSION, INFERENCE_PREDICTION_VERSION,
    INFERENCE_CONFIDENCE_VERSION, INFERENCE_CALIBRATION_VERSION,
    INFERENCE_EXPLAINABILITY_VERSION, INFERENCE_REGISTRY_VERSION, INFERENCE_VALIDATION_VERSION,
    DETERMINISTIC_EPOCH, FINGERPRINT_DECIMALS,
)


def _q(x: float) -> float:
    return round(float(x), FINGERPRINT_DECIMALS)


def _qlist(values) -> list:
    return [round(float(v), FINGERPRINT_DECIMALS) for v in values]


# =============================================================================
# Closed vocabularies (no free-form states)
# =============================================================================
class ConfidenceLevel(str, Enum):
    """A closed confidence band derived from the prediction reliability."""

    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        if score >= 0.85:
            return cls.HIGH
        if score >= 0.65:
            return cls.MODERATE
        if score >= 0.45:
            return cls.LOW
        return cls.VERY_LOW


class CalibrationQuality(str, Enum):
    """A closed calibration band derived from the Expected Calibration Error."""

    WELL_CALIBRATED = "well_calibrated"
    MODERATELY_CALIBRATED = "moderately_calibrated"
    POORLY_CALIBRATED = "poorly_calibrated"

    @classmethod
    def from_ece(cls, ece: float) -> "CalibrationQuality":
        if ece <= 0.10:
            return cls.WELL_CALIBRATED
        if ece <= 0.25:
            return cls.MODERATELY_CALIBRATED
        return cls.POORLY_CALIBRATED


class ExplanationMethod(str, Enum):
    """The closed set of explanation methods (structured attribution only)."""

    OCCLUSION = "occlusion"
    INPUT_SALIENCE = "input_salience"


class InferenceStatus(str, Enum):
    """The standing of an inference (prediction) asset (deliberately tiny)."""

    GENERATED = "generated"
    QUARANTINED = "quarantined"


# =============================================================================
# Identity projection
# =============================================================================
@dataclass(frozen=True)
class InferenceIdentity:
    """A prediction-asset identity, content-addressed from its model + input feature.
    Never filename-derived."""

    prediction_id: str
    model_id: str
    feature_asset_id: str
    identity_version: str
    domain_version: str = INFERENCE_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {
            "prediction_id": self.prediction_id, "model_id": self.model_id,
            "feature_asset_id": self.feature_asset_id, "identity_version": self.identity_version,
            "domain_version": self.domain_version,
        }


# =============================================================================
# Prediction projections
# =============================================================================
@dataclass(frozen=True)
class PredictionClass:
    """One candidate class: index, label, and its probability."""

    class_index: int
    class_label: str
    probability: float

    def to_dict(self) -> dict:
        return {"class_index": self.class_index, "class_label": self.class_label,
                "probability": _q(self.probability)}


@dataclass(frozen=True)
class PredictionScore:
    """A named scalar score (e.g. logit / margin / entropy) for the prediction."""

    name: str
    value: float

    def to_dict(self) -> dict:
        return {"name": self.name, "value": _q(self.value)}


@dataclass(frozen=True)
class PredictionRecord:
    """The core prediction result — predicted class + class probabilities + scores."""

    predicted_class: int
    predicted_label: str
    classes: tuple[PredictionClass, ...]
    scores: tuple[PredictionScore, ...]
    decision_metadata: dict
    prediction_version: str = INFERENCE_PREDICTION_VERSION

    @property
    def probabilities(self) -> tuple[float, ...]:
        return tuple(c.probability for c in self.classes)

    def signature(self) -> str:
        return hash_obj({
            "predicted_class": self.predicted_class, "predicted_label": self.predicted_label,
            "classes": [c.to_dict() for c in self.classes],
            "scores": [s.to_dict() for s in self.scores]})

    def to_dict(self) -> dict:
        return {
            "predicted_class": self.predicted_class, "predicted_label": self.predicted_label,
            "classes": [c.to_dict() for c in self.classes], "scores": [s.to_dict() for s in self.scores],
            "decision_metadata": dict(sorted(self.decision_metadata.items())),
            "prediction_version": self.prediction_version, "prediction_signature": self.signature(),
        }


# =============================================================================
# Confidence projection
# =============================================================================
@dataclass(frozen=True)
class ConfidenceRecord:
    """Deterministic confidence assessment of a prediction."""

    confidence_score: float
    confidence_interval: tuple[float, float]
    prediction_stability: float
    prediction_reliability: float
    uncertainty_summary: dict
    confidence_level: ConfidenceLevel
    confidence_version: str = INFERENCE_CONFIDENCE_VERSION

    def signature(self) -> str:
        return hash_obj({
            "confidence_score": _q(self.confidence_score),
            "confidence_interval": _qlist(self.confidence_interval),
            "prediction_stability": _q(self.prediction_stability),
            "prediction_reliability": _q(self.prediction_reliability),
            "uncertainty_summary": {k: _q(v) if isinstance(v, (int, float)) else v
                                    for k, v in sorted(self.uncertainty_summary.items())},
            "confidence_level": self.confidence_level.value})

    def to_dict(self) -> dict:
        return {
            "confidence_score": _q(self.confidence_score),
            "confidence_interval": _qlist(self.confidence_interval),
            "prediction_stability": _q(self.prediction_stability),
            "prediction_reliability": _q(self.prediction_reliability),
            "uncertainty_summary": {k: (_q(v) if isinstance(v, (int, float)) else v)
                                    for k, v in sorted(self.uncertainty_summary.items())},
            "confidence_level": self.confidence_level.value,
            "confidence_version": self.confidence_version, "confidence_signature": self.signature(),
        }


# =============================================================================
# Calibration projection
# =============================================================================
@dataclass(frozen=True)
class CalibrationRecord:
    """Deterministic probability-calibration assessment (reference + per-prediction)."""

    expected_calibration_error: float
    brier_score: float
    reliability_assessment: float
    confidence_consistency: float
    calibration_quality: CalibrationQuality
    reference_n_samples: int
    calibration_version: str = INFERENCE_CALIBRATION_VERSION

    def signature(self) -> str:
        return hash_obj({
            "expected_calibration_error": _q(self.expected_calibration_error),
            "brier_score": _q(self.brier_score),
            "reliability_assessment": _q(self.reliability_assessment),
            "confidence_consistency": _q(self.confidence_consistency),
            "calibration_quality": self.calibration_quality.value,
            "reference_n_samples": self.reference_n_samples})

    def to_dict(self) -> dict:
        return {
            "expected_calibration_error": _q(self.expected_calibration_error),
            "brier_score": _q(self.brier_score),
            "reliability_assessment": _q(self.reliability_assessment),
            "confidence_consistency": _q(self.confidence_consistency),
            "calibration_quality": self.calibration_quality.value,
            "reference_n_samples": self.reference_n_samples,
            "calibration_version": self.calibration_version,
            "calibration_signature": self.signature(),
        }


# =============================================================================
# Explanation projection
# =============================================================================
@dataclass(frozen=True)
class FeatureContribution:
    """One feature's signed contribution to the predicted class."""

    name: str
    contribution: float

    def to_dict(self) -> dict:
        return {"name": self.name, "contribution": _q(self.contribution)}


@dataclass(frozen=True)
class ExplanationRecord:
    """Structured (no-image) explanation of a prediction."""

    method: ExplanationMethod
    feature_contributions: tuple[FeatureContribution, ...]
    feature_importance: tuple[FeatureContribution, ...]
    band_importance: dict
    channel_importance: dict
    decision_factors: tuple[dict, ...]
    model_attribution_summary: dict
    explanation_version: str = INFERENCE_EXPLAINABILITY_VERSION

    def signature(self) -> str:
        return hash_obj({
            "method": self.method.value,
            "feature_contributions": [c.to_dict() for c in self.feature_contributions],
            "band_importance": {k: _q(v) for k, v in sorted(self.band_importance.items())},
            "channel_importance": {k: _q(v) for k, v in sorted(self.channel_importance.items())},
            "decision_factors": [dict(sorted(d.items())) for d in self.decision_factors]})

    def to_dict(self) -> dict:
        return {
            "method": self.method.value,
            "feature_contributions": [c.to_dict() for c in self.feature_contributions],
            "feature_importance": [c.to_dict() for c in self.feature_importance],
            "band_importance": {k: _q(v) for k, v in sorted(self.band_importance.items())},
            "channel_importance": {k: _q(v) for k, v in sorted(self.channel_importance.items())},
            "decision_factors": [dict(sorted(d.items())) for d in self.decision_factors],
            "model_attribution_summary": dict(sorted(self.model_attribution_summary.items())),
            "explanation_version": self.explanation_version, "explanation_signature": self.signature(),
        }


# =============================================================================
# Validation / audit / lineage / version projections
# =============================================================================
@dataclass(frozen=True)
class InferenceValidationRecord:
    """A persisted projection of the inference validation (build-time content checks)."""

    validation_id: str
    ok: bool
    checks: tuple[tuple, ...]            # (name, passed, detail)
    validation_version: str = INFERENCE_VALIDATION_VERSION

    @property
    def n_checks(self) -> int:
        return len(self.checks)

    def signature(self) -> str:
        return hash_obj({"ok": self.ok, "checks": [[n, bool(p)] for n, p, _ in self.checks]})

    def to_dict(self) -> dict:
        return {
            "validation_id": self.validation_id, "ok": self.ok, "n_checks": self.n_checks,
            "checks": [{"name": n, "passed": bool(p), "detail": d} for n, p, d in self.checks],
            "validation_version": self.validation_version, "validation_signature": self.signature(),
        }


@dataclass(frozen=True)
class InferenceAuditRecord:
    """An immutable audit event in the hash-chained inference audit log (shared log)."""

    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {
            "seq": self.seq, "kind": self.kind, "payload": self.payload,
            "prev_hash": self.prev_hash, "event_hash": self.event_hash, "created_at": self.created_at,
        }


@dataclass(frozen=True)
class InferenceLineageRecord:
    """A projection of the shared lineage node attached to a prediction asset."""

    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


@dataclass(frozen=True)
class PredictionVersion:
    """A content-addressed prediction-asset version (chained like ModelVersion)."""

    version: str
    previous: Optional[str]
    reason: str
    created_at: str = DETERMINISTIC_EPOCH

    @staticmethod
    def compute(state_signature: str, previous: Optional[str]) -> str:
        return hash_obj({"state": state_signature, "previous": previous})

    def to_dict(self) -> dict:
        return {"version": self.version, "previous": self.previous,
                "reason": self.reason, "created_at": self.created_at}


# =============================================================================
# Registry record
# =============================================================================
@dataclass
class InferenceRegistryRecord:
    """The registry entry shape (mutated only via governed registry methods)."""

    prediction_id: str
    model_id: str
    feature_asset_id: str
    case_id: str
    patient_id: str
    predicted_class: int
    confidence_level: str
    calibration_quality: str
    status: InferenceStatus
    version: str
    owner: str
    creation_date: str
    audit_state: str
    lineage_id: str
    dependencies: tuple[str, ...]
    inference_registry_version: str = INFERENCE_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({
            "prediction_id": self.prediction_id, "model_id": self.model_id,
            "feature_asset_id": self.feature_asset_id, "predicted_class": self.predicted_class,
            "status": self.status.value, "version": self.version, "lineage_id": self.lineage_id})

    def to_dict(self) -> dict:
        return {
            "prediction_id": self.prediction_id, "model_id": self.model_id,
            "feature_asset_id": self.feature_asset_id, "case_id": self.case_id,
            "patient_id": self.patient_id, "predicted_class": self.predicted_class,
            "confidence_level": self.confidence_level, "calibration_quality": self.calibration_quality,
            "status": self.status.value, "version": self.version, "owner": self.owner,
            "creation_date": self.creation_date, "audit_state": self.audit_state,
            "lineage_id": self.lineage_id, "dependencies": list(self.dependencies),
            "inference_registry_version": self.inference_registry_version,
            "content_signature": self.content_signature(),
        }


# =============================================================================
# The aggregate — the immutable Prediction (Inference) asset
# =============================================================================
@dataclass(frozen=True)
class InferenceRecord:
    """The inference aggregate — an **immutable**, versioned, auditable, lineage-tracked
    prediction asset. Bundles the prediction, confidence, calibration, and explanation
    records + execution/model/feature metadata, the validation record, status, version,
    owner, lineage node, and audit-log head. It carries no model weights and no raw
    signal — only derived, content-addressed prediction artifacts."""

    identity: InferenceIdentity
    model_id: str
    feature_asset_id: str
    case_id: str
    patient_id: str
    prediction: PredictionRecord
    confidence: ConfidenceRecord
    calibration: CalibrationRecord
    explanation: ExplanationRecord
    execution_metadata: dict
    model_metadata: dict
    feature_metadata: dict
    validation: InferenceValidationRecord
    status: InferenceStatus
    version: PredictionVersion
    owner: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    dependencies: tuple[str, ...] = ()
    domain_version: str = INFERENCE_DOMAIN_VERSION

    @property
    def prediction_id(self) -> str:
        return self.identity.prediction_id

    @staticmethod
    def state_signature_of(*, identity, model_id, feature_asset_id, case_id, patient_id,
                           prediction, confidence, calibration, explanation, execution_metadata,
                           validation, status, dependencies) -> str:
        return hash_obj({
            "prediction_id": identity.prediction_id, "model_id": model_id,
            "feature_asset_id": feature_asset_id, "case_id": case_id, "patient_id": patient_id,
            "prediction_signature": prediction.signature(),
            "confidence_signature": confidence.signature(),
            "calibration_signature": calibration.signature(),
            "explanation_signature": explanation.signature(),
            "execution_metadata": dict(sorted(execution_metadata.items())),
            "validation_signature": validation.signature(), "status": status.value,
            "dependencies": list(dependencies)})

    def state_signature(self) -> str:
        return self.state_signature_of(
            identity=self.identity, model_id=self.model_id, feature_asset_id=self.feature_asset_id,
            case_id=self.case_id, patient_id=self.patient_id, prediction=self.prediction,
            confidence=self.confidence, calibration=self.calibration, explanation=self.explanation,
            execution_metadata=self.execution_metadata, validation=self.validation,
            status=self.status, dependencies=self.dependencies)

    def to_dict(self) -> dict:
        return {
            "domain_version": self.domain_version, "identity": self.identity.to_dict(),
            "model_id": self.model_id, "feature_asset_id": self.feature_asset_id,
            "case_id": self.case_id, "patient_id": self.patient_id,
            "prediction": self.prediction.to_dict(), "confidence": self.confidence.to_dict(),
            "calibration": self.calibration.to_dict(), "explanation": self.explanation.to_dict(),
            "execution_metadata": dict(sorted(self.execution_metadata.items())),
            "model_metadata": dict(sorted(self.model_metadata.items())),
            "feature_metadata": dict(sorted(self.feature_metadata.items())),
            "validation": self.validation.to_dict(), "status": self.status.value,
            "version": self.version.to_dict(), "owner": self.owner, "created_at": self.created_at,
            "lineage_id": self.lineage_id, "audit_head": self.audit_head,
            "dependencies": list(self.dependencies), "state_signature": self.state_signature(),
        }
