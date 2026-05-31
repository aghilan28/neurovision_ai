"""Serving Platform domain entities + closed vocabularies (DRP3-B).

Pure data shapes (JSON-able, content-hashable). No I/O, no orchestration, no prediction
logic — this module owns only the *shapes* and the *closed vocabularies* (no free-form
states). The serving engine / prediction service / lifecycle / validation / readiness
engines produce these records; the service assembles the immutable
``ServingExecutionRecord`` aggregate.

Mirrors ``backend.inference_foundation.models.domain`` so the serving layer is shaped
exactly like the rest of the platform (NR-6). Determinism (NR-9/NR-10): every
``signature()`` and content id is a function of deterministic fields only — there is no
wall-clock and no randomness anywhere in the serving path.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    SERVING_DOMAIN_VERSION, SERVING_LIFECYCLE_VERSION,
    SERVING_READINESS_VERSION, SERVING_REGISTRY_VERSION, SERVING_VALIDATION_VERSION,
    DETERMINISTIC_EPOCH, FINGERPRINT_DECIMALS,
)


def _q(x) -> float:
    return round(float(x), FINGERPRINT_DECIMALS)


def _qlist(xs) -> list:
    return [_q(v) for v in xs]


# =============================================================================
# Closed vocabularies (no free-form states)
# =============================================================================
class LifecycleState(str, Enum):
    """The closed ordered serving execution lifecycle (DRP3-F)."""

    REQUEST_CREATED = "request_created"
    REQUEST_VALIDATED = "request_validated"
    MODEL_SELECTED = "model_selected"
    INFERENCE_EXECUTED = "inference_executed"
    RESPONSE_GENERATED = "response_generated"
    RESPONSE_DELIVERED = "response_delivered"
    EXECUTION_COMPLETED = "execution_completed"


# The canonical forward order of the lifecycle.
LIFECYCLE_ORDER: tuple[LifecycleState, ...] = (
    LifecycleState.REQUEST_CREATED, LifecycleState.REQUEST_VALIDATED, LifecycleState.MODEL_SELECTED,
    LifecycleState.INFERENCE_EXECUTED, LifecycleState.RESPONSE_GENERATED,
    LifecycleState.RESPONSE_DELIVERED, LifecycleState.EXECUTION_COMPLETED,
)


class ServingStatus(str, Enum):
    """The overall outcome of a serving execution."""

    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class ResponseStatus(str, Enum):
    DELIVERED = "delivered"
    ERROR = "error"


class ReadinessClass(str, Enum):
    NOT_READY = "NOT_READY"
    PARTIALLY_READY = "PARTIALLY_READY"
    READY = "READY"


class ReadinessDimension(str, Enum):
    """The closed set of serving-readiness dimensions (DRP3-I)."""

    EXECUTION = "execution_readiness"
    CONTRACT = "contract_readiness"
    VALIDATION = "validation_readiness"
    REGISTRY = "registry_readiness"
    AUDIT = "audit_readiness"
    LINEAGE = "lineage_readiness"


class EntityKind(str, Enum):
    """The kinds of entity tracked in the serving registry."""

    REQUEST = "serving_request"
    EXECUTION = "serving_execution"
    RESPONSE = "serving_response"
    CONTRACT = "serving_contract"
    READINESS = "serving_readiness"


# =============================================================================
# Identity + versioning projections
# =============================================================================
@dataclass(frozen=True)
class ServingIdentity:
    """A serving-execution identity, content-addressed from its request + prediction."""

    execution_id: str
    request_id: str
    response_id: str
    model_id: str
    prediction_id: str
    identity_version: str
    domain_version: str = SERVING_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id, "request_id": self.request_id,
            "response_id": self.response_id, "model_id": self.model_id,
            "prediction_id": self.prediction_id, "identity_version": self.identity_version,
            "domain_version": self.domain_version,
        }


@dataclass(frozen=True)
class ServingVersion:
    """A content-addressed serving-execution version."""

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
# Request / response / lifecycle
# =============================================================================
@dataclass(frozen=True)
class ServingRequestRecord:
    """A received prediction request (a model reference + the input recording)."""

    request_id: str
    model_ref: dict
    feature_asset_id: str
    case_id: str
    patient_id: str
    requested_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None

    def signature(self) -> str:
        return hash_obj({
            "request_id": self.request_id, "model_ref": dict(sorted(self.model_ref.items())),
            "feature_asset_id": self.feature_asset_id, "case_id": self.case_id,
            "patient_id": self.patient_id,
        })

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id, "model_ref": dict(sorted(self.model_ref.items())),
            "feature_asset_id": self.feature_asset_id, "case_id": self.case_id,
            "patient_id": self.patient_id, "requested_at": self.requested_at,
            "lineage_id": self.lineage_id, "audit_state": self.audit_state,
            "request_signature": self.signature(),
        }


@dataclass(frozen=True)
class ServingResponseRecord:
    """A generated prediction response — the delivery surface (DRP3-D).

    Carries the predicted class + probability scores + confidence + calibration +
    explanation summary, all sourced from the reused inference-foundation asset."""

    response_id: str
    request_id: str
    model_id: str
    prediction_id: str
    predicted_class: int
    probability_scores: tuple[float, ...]
    confidence_level: str
    confidence_score: float
    calibration_quality: str
    expected_calibration_error: float
    explanation_summary: tuple[dict, ...]
    status: ResponseStatus
    error: Optional[dict] = None
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None

    def signature(self) -> str:
        return hash_obj({
            "response_id": self.response_id, "request_id": self.request_id,
            "model_id": self.model_id, "prediction_id": self.prediction_id,
            "predicted_class": self.predicted_class,
            "probability_scores": _qlist(self.probability_scores),
            "confidence_level": self.confidence_level, "confidence_score": _q(self.confidence_score),
            "calibration_quality": self.calibration_quality,
            "expected_calibration_error": _q(self.expected_calibration_error),
            "explanation_summary": [dict(sorted(c.items())) for c in self.explanation_summary],
            "status": self.status.value, "error": self.error,
        })

    def to_dict(self) -> dict:
        return {
            "response_id": self.response_id, "request_id": self.request_id,
            "model_id": self.model_id, "prediction_id": self.prediction_id,
            "predicted_class": self.predicted_class,
            "probability_scores": _qlist(self.probability_scores),
            "confidence_level": self.confidence_level, "confidence_score": _q(self.confidence_score),
            "calibration_quality": self.calibration_quality,
            "expected_calibration_error": _q(self.expected_calibration_error),
            "explanation_summary": [dict(sorted(c.items())) for c in self.explanation_summary],
            "status": self.status.value, "error": self.error, "created_at": self.created_at,
            "lineage_id": self.lineage_id, "response_signature": self.signature(),
        }


@dataclass(frozen=True)
class ServingLifecycleRecord:
    """The tracked lifecycle transitions for one serving execution (DRP3-F)."""

    request_id: str
    transitions: tuple[tuple, ...]            # (state_value, detail)
    final_state: str
    lifecycle_version: str = SERVING_LIFECYCLE_VERSION

    @property
    def states(self) -> tuple[str, ...]:
        return tuple(s for s, _ in self.transitions)

    def signature(self) -> str:
        return hash_obj({"request_id": self.request_id, "states": list(self.states),
                         "final_state": self.final_state})

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id, "final_state": self.final_state,
            "transitions": [{"state": s, "detail": d} for s, d in self.transitions],
            "lifecycle_version": self.lifecycle_version, "lifecycle_signature": self.signature(),
        }


# =============================================================================
# Validation / readiness projections
# =============================================================================
@dataclass(frozen=True)
class ServingValidationRecord:
    validation_id: str
    ok: bool
    checks: tuple[tuple, ...]            # (name, passed, detail)
    validation_version: str = SERVING_VALIDATION_VERSION

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
class ServingReadinessRecord:
    readiness_id: str
    target_id: str
    score: float
    classification: ReadinessClass
    dimensions: dict
    findings: tuple[str, ...]
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    readiness_version: str = SERVING_READINESS_VERSION

    def signature(self) -> str:
        return hash_obj({
            "readiness_id": self.readiness_id, "target_id": self.target_id, "score": _q(self.score),
            "classification": self.classification.value,
            "dimensions": {k: _q(v) for k, v in sorted(self.dimensions.items())},
            "findings": list(self.findings),
        })

    def to_dict(self) -> dict:
        return {
            "readiness_id": self.readiness_id, "target_id": self.target_id, "score": _q(self.score),
            "classification": self.classification.value,
            "dimensions": {k: _q(v) for k, v in sorted(self.dimensions.items())},
            "findings": list(self.findings), "created_at": self.created_at,
            "lineage_id": self.lineage_id, "readiness_version": self.readiness_version,
            "readiness_signature": self.signature(),
        }


# =============================================================================
# Audit / lineage projections
# =============================================================================
@dataclass(frozen=True)
class ServingAuditRecord:
    """An immutable audit event in the hash-chained serving audit log (the shared
    ``ImmutableAuditLog`` implementation; no parallel system)."""

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
class ServingLineageRecord:
    """A projection of a shared lineage node attached to a serving artifact."""

    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


# =============================================================================
# Registry record
# =============================================================================
@dataclass
class ServingRegistryRecord:
    """The serving registry entry shape (mutated only via governed registry methods).
    Cross-references the shared model id + the reused inference prediction id (no parallel
    model / prediction registry is created)."""

    execution_id: str
    request_id: str
    response_id: str
    model_id: str
    prediction_id: str
    feature_asset_id: str
    case_id: str
    patient_id: str
    status: ServingStatus
    readiness_id: str
    version: str
    owner: str
    creation_date: str
    audit_state: str
    lineage_id: str
    dependencies: tuple[str, ...]
    registry_version: str = SERVING_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({
            "execution_id": self.execution_id, "request_id": self.request_id,
            "response_id": self.response_id, "model_id": self.model_id,
            "prediction_id": self.prediction_id, "status": self.status.value,
            "readiness_id": self.readiness_id, "version": self.version, "lineage_id": self.lineage_id,
        })

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id, "request_id": self.request_id,
            "response_id": self.response_id, "model_id": self.model_id,
            "prediction_id": self.prediction_id, "feature_asset_id": self.feature_asset_id,
            "case_id": self.case_id, "patient_id": self.patient_id, "status": self.status.value,
            "readiness_id": self.readiness_id, "version": self.version, "owner": self.owner,
            "creation_date": self.creation_date, "audit_state": self.audit_state,
            "lineage_id": self.lineage_id, "dependencies": list(self.dependencies),
            "registry_version": self.registry_version, "content_signature": self.content_signature(),
        }


# =============================================================================
# The aggregate — the immutable Serving Execution
# =============================================================================
@dataclass(frozen=True)
class ServingExecutionRecord:
    """The serving aggregate — an **immutable**, versioned, auditable, lineage-tracked
    record of one served execution. Binds the request, the selected model, the reused
    inference prediction, the generated response, the lifecycle, the validation, and the
    readiness assessment. Carries derived ids + signatures, never model weights."""

    identity: ServingIdentity
    request: ServingRequestRecord
    response: ServingResponseRecord
    lifecycle: ServingLifecycleRecord
    model_id: str
    prediction_id: str
    feature_asset_id: str
    case_id: str
    patient_id: str
    validation: ServingValidationRecord
    readiness_id: str
    readiness_class: ReadinessClass
    status: ServingStatus
    version: ServingVersion
    owner: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    dependencies: tuple[str, ...] = ()
    domain_version: str = SERVING_DOMAIN_VERSION

    @property
    def execution_id(self) -> str:
        return self.identity.execution_id

    @property
    def request_id(self) -> str:
        return self.identity.request_id

    @property
    def response_id(self) -> str:
        return self.identity.response_id

    @staticmethod
    def state_signature_of(*, identity, request, response, lifecycle, model_id, prediction_id,
                           feature_asset_id, case_id, patient_id, validation, readiness_id,
                           readiness_class, status, dependencies) -> str:
        return hash_obj({
            "execution_id": identity.execution_id, "request_signature": request.signature(),
            "response_signature": response.signature(), "lifecycle_signature": lifecycle.signature(),
            "model_id": model_id, "prediction_id": prediction_id,
            "feature_asset_id": feature_asset_id, "case_id": case_id, "patient_id": patient_id,
            "validation_signature": validation.signature(), "readiness_id": readiness_id,
            "readiness_class": readiness_class.value, "status": status.value,
            "dependencies": list(dependencies),
        })

    def state_signature(self) -> str:
        return self.state_signature_of(
            identity=self.identity, request=self.request, response=self.response,
            lifecycle=self.lifecycle, model_id=self.model_id, prediction_id=self.prediction_id,
            feature_asset_id=self.feature_asset_id, case_id=self.case_id, patient_id=self.patient_id,
            validation=self.validation, readiness_id=self.readiness_id,
            readiness_class=self.readiness_class, status=self.status, dependencies=self.dependencies)

    def to_dict(self) -> dict:
        return {
            "domain_version": self.domain_version, "identity": self.identity.to_dict(),
            "request": self.request.to_dict(), "response": self.response.to_dict(),
            "lifecycle": self.lifecycle.to_dict(), "model_id": self.model_id,
            "prediction_id": self.prediction_id, "feature_asset_id": self.feature_asset_id,
            "case_id": self.case_id, "patient_id": self.patient_id,
            "validation": self.validation.to_dict(), "readiness_id": self.readiness_id,
            "readiness_class": self.readiness_class.value, "status": self.status.value,
            "version": self.version.to_dict(), "owner": self.owner, "created_at": self.created_at,
            "lineage_id": self.lineage_id, "audit_head": self.audit_head,
            "dependencies": list(self.dependencies), "state_signature": self.state_signature(),
        }
