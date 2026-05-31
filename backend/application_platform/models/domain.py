"""Application Platform domain entities + closed vocabularies (Track 3, T3-B).

Pure, JSON-able, content-hashable records describing the **product** layer: user requests,
uploads, prediction requests/results, analyses, reports, workflow executions, readiness,
and registry/audit/lineage projections. No I/O and no orchestration here — only the shapes
and the closed vocabularies (NR-6: reuse the platform domain-model shape).

These records project the real workflow run by the reused ``application_backend`` hub over
real EEG files + real trained models; they carry no signal arrays or model weights — only
governed metadata, content fingerprints, and cross-references to the audit head + lineage
node. Determinism (NR-9/NR-10): ids/fingerprints are content-addressed; the only
non-deterministic inputs (auth secrets) are quarantined upstream by ``application_backend``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    APP_PREDICTION_VERSION, APP_READINESS_VERSION, APP_REGISTRY_VERSION,
    APP_REPORT_VERSION, APP_UPLOAD_VERSION, APP_WORKFLOW_VERSION, DETERMINISTIC_EPOCH,
    FINGERPRINT_DECIMALS,
)


def _q(x: float) -> float:
    return round(float(x), FINGERPRINT_DECIMALS)


# =============================================================================
# Closed vocabularies
# =============================================================================
class UploadFormat(str, Enum):
    EDF = "edf"
    EDF_PLUS = "edf_plus"
    BDF = "bdf"
    BDF_PLUS = "bdf_plus"


class UploadStatus(str, Enum):
    RECEIVED = "received"
    VALIDATED = "validated"
    REJECTED = "rejected"


class WorkflowStage(str, Enum):
    UPLOAD = "upload"
    VALIDATE = "validate"
    METADATA = "metadata"
    FEATURES = "features"
    SELECT_MODEL = "select_model"
    INFERENCE = "inference"
    RESULTS = "results"
    REPORT = "report"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class RequestStatus(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ReportFormat(str, Enum):
    JSON = "json"
    HTML = "html"
    PDF = "pdf"


class ApplicationReadinessClass(str, Enum):
    NOT_READY = "NOT_READY"
    PARTIALLY_READY = "PARTIALLY_READY"
    READY_FOR_USERS = "READY_FOR_USERS"


class ReadinessDimension(str, Enum):
    UPLOAD = "upload_readiness"
    PREDICTION = "prediction_readiness"
    WORKFLOW = "workflow_readiness"
    REPORT = "report_readiness"
    REGISTRY = "registry_readiness"
    AUDIT = "audit_readiness"
    LINEAGE = "lineage_readiness"


class EntityKind(str, Enum):
    UPLOAD = "app_upload"
    PREDICTION_REQUEST = "app_prediction_request"
    PREDICTION_RESULT = "app_prediction_result"
    ANALYSIS = "app_analysis"
    REPORT = "app_report"
    WORKFLOW = "app_workflow"
    READINESS = "app_readiness"


# =============================================================================
# T3-B — domain records
# =============================================================================
@dataclass(frozen=True)
class UserRequestRecord:
    request_id: str
    operation: str
    api_version: str
    user_id: Optional[str]
    params_fingerprint: str
    status: RequestStatus
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {"request_id": self.request_id, "operation": self.operation,
                "api_version": self.api_version, "user_id": self.user_id,
                "params_fingerprint": self.params_fingerprint, "status": self.status.value,
                "created_at": self.created_at}


@dataclass(frozen=True)
class UploadRecord:
    upload_id: str
    user_id: str
    filename: str
    fmt: UploadFormat
    content_fingerprint: str
    size_bytes: int
    analysis_seconds: float
    sampling_frequency: float
    n_channels: int
    duration_seconds: float
    status: UploadStatus
    findings: tuple = ()
    backend_upload_id: Optional[str] = None
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    upload_version: str = APP_UPLOAD_VERSION

    def to_dict(self) -> dict:
        return {"upload_id": self.upload_id, "user_id": self.user_id, "filename": self.filename,
                "format": self.fmt.value, "content_fingerprint": self.content_fingerprint,
                "size_bytes": self.size_bytes, "analysis_seconds": _q(self.analysis_seconds),
                "sampling_frequency": _q(self.sampling_frequency), "n_channels": self.n_channels,
                "duration_seconds": _q(self.duration_seconds), "status": self.status.value,
                "findings": list(self.findings), "backend_upload_id": self.backend_upload_id,
                "created_at": self.created_at, "lineage_id": self.lineage_id,
                "audit_head": self.audit_head, "upload_version": self.upload_version}


@dataclass(frozen=True)
class PredictionRequestRecord:
    prediction_request_id: str
    upload_id: str
    user_id: str
    model_id: str
    architecture: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {"prediction_request_id": self.prediction_request_id, "upload_id": self.upload_id,
                "user_id": self.user_id, "model_id": self.model_id,
                "architecture": self.architecture, "created_at": self.created_at,
                "lineage_id": self.lineage_id}


@dataclass(frozen=True)
class PredictionResultRecord:
    prediction_result_id: str
    prediction_request_id: str
    predicted_class: int
    predicted_label: str
    confidence_level: str
    confidence_score: float
    calibration_quality: str
    model_id: str
    model_architecture: str
    model_readiness: str
    evidence: dict = field(default_factory=dict)
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    prediction_version: str = APP_PREDICTION_VERSION

    def signature(self) -> str:
        return hash_obj({"prediction_request_id": self.prediction_request_id,
                         "predicted_class": self.predicted_class,
                         "predicted_label": self.predicted_label,
                         "confidence_level": self.confidence_level,
                         "calibration_quality": self.calibration_quality,
                         "model_id": self.model_id})

    def to_dict(self) -> dict:
        return {"prediction_result_id": self.prediction_result_id,
                "prediction_request_id": self.prediction_request_id,
                "predicted_class": self.predicted_class, "predicted_label": self.predicted_label,
                "confidence_level": self.confidence_level,
                "confidence_score": _q(self.confidence_score),
                "calibration_quality": self.calibration_quality, "model_id": self.model_id,
                "model_architecture": self.model_architecture,
                "model_readiness": self.model_readiness, "evidence": self.evidence,
                "created_at": self.created_at, "lineage_id": self.lineage_id,
                "prediction_version": self.prediction_version, "signature": self.signature()}


@dataclass(frozen=True)
class AnalysisRecord:
    analysis_id: str
    upload_id: str
    user_id: str
    workflow_id: str
    backend_analysis_id: str
    prediction_request_id: str
    prediction_result_id: str
    status: WorkflowStatus
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {"analysis_id": self.analysis_id, "upload_id": self.upload_id,
                "user_id": self.user_id, "workflow_id": self.workflow_id,
                "backend_analysis_id": self.backend_analysis_id,
                "prediction_request_id": self.prediction_request_id,
                "prediction_result_id": self.prediction_result_id, "status": self.status.value,
                "created_at": self.created_at, "lineage_id": self.lineage_id}


@dataclass(frozen=True)
class ReportRecord:
    report_id: str
    analysis_id: str
    report_type: str
    available_formats: tuple
    content_fingerprint: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    report_version: str = APP_REPORT_VERSION

    def to_dict(self) -> dict:
        return {"report_id": self.report_id, "analysis_id": self.analysis_id,
                "report_type": self.report_type, "available_formats": list(self.available_formats),
                "content_fingerprint": self.content_fingerprint, "created_at": self.created_at,
                "lineage_id": self.lineage_id, "report_version": self.report_version}


@dataclass(frozen=True)
class WorkflowRecord:
    workflow_id: str
    upload_id: str
    user_id: str
    analysis_id: str
    stages: tuple
    status: WorkflowStatus
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    workflow_version: str = APP_WORKFLOW_VERSION

    def signature(self) -> str:
        return hash_obj({"workflow_id": self.workflow_id, "upload_id": self.upload_id,
                         "analysis_id": self.analysis_id, "stages": list(self.stages),
                         "status": self.status.value})

    def to_dict(self) -> dict:
        return {"workflow_id": self.workflow_id, "upload_id": self.upload_id,
                "user_id": self.user_id, "analysis_id": self.analysis_id,
                "stages": list(self.stages), "status": self.status.value,
                "created_at": self.created_at, "lineage_id": self.lineage_id,
                "audit_head": self.audit_head, "workflow_version": self.workflow_version,
                "signature": self.signature()}


@dataclass(frozen=True)
class ReadinessRecord:
    readiness_id: str
    subject: str
    score: float
    classification: ApplicationReadinessClass
    dimensions: dict
    findings: tuple
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    readiness_version: str = APP_READINESS_VERSION

    def to_dict(self) -> dict:
        return {"readiness_id": self.readiness_id, "subject": self.subject, "score": _q(self.score),
                "classification": self.classification.value,
                "dimensions": dict(sorted(self.dimensions.items())), "findings": list(self.findings),
                "created_at": self.created_at, "lineage_id": self.lineage_id,
                "readiness_version": self.readiness_version}


@dataclass(frozen=True)
class ValidationRecord:
    validation_id: str
    ok: bool
    checks: tuple                            # (name, passed, detail)

    @property
    def n_checks(self) -> int:
        return len(self.checks)

    def to_dict(self) -> dict:
        return {"validation_id": self.validation_id, "ok": self.ok, "n_checks": self.n_checks,
                "checks": [{"name": n, "passed": bool(p), "detail": d} for n, p, d in self.checks]}


# =============================================================================
# Registry / audit / lineage projections
# =============================================================================
@dataclass
class ApplicationRegistryRecord:
    entity_kind: EntityKind
    entity_id: str
    status: str
    version: str
    owner: str
    creation_date: str
    audit_state: str
    lineage_id: str
    dependencies: tuple = ()
    registry_version: str = APP_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"entity_kind": self.entity_kind.value, "entity_id": self.entity_id,
                         "status": self.status, "version": self.version,
                         "lineage_id": self.lineage_id, "audit_state": self.audit_state})

    def to_dict(self) -> dict:
        return {"entity_kind": self.entity_kind.value, "entity_id": self.entity_id,
                "status": self.status, "version": self.version, "owner": self.owner,
                "creation_date": self.creation_date, "audit_state": self.audit_state,
                "lineage_id": self.lineage_id, "dependencies": list(self.dependencies),
                "registry_version": self.registry_version,
                "content_signature": self.content_signature()}


@dataclass(frozen=True)
class ApplicationAuditRecord:
    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {"seq": self.seq, "kind": self.kind, "payload": self.payload,
                "prev_hash": self.prev_hash, "event_hash": self.event_hash,
                "created_at": self.created_at}


__all__ = [
    "UploadFormat", "UploadStatus", "WorkflowStage", "WorkflowStatus", "RequestStatus",
    "ReportFormat", "ApplicationReadinessClass", "ReadinessDimension", "EntityKind",
    "UserRequestRecord", "UploadRecord", "PredictionRequestRecord", "PredictionResultRecord",
    "AnalysisRecord", "ReportRecord", "WorkflowRecord", "ReadinessRecord", "ValidationRecord",
    "ApplicationRegistryRecord", "ApplicationAuditRecord",
]
