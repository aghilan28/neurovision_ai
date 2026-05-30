"""Application Backend domain entities + closed vocabularies (Productization P6).

Pure data shapes (JSON-able, content-hashable). No I/O, no orchestration, no service
execution — this module owns only the *shapes* and the *closed vocabularies* (no
free-form states). The auth / user / workflow / api services produce these records.

Mirrors ``backend.inference_foundation.models.domain`` so the application layer is
shaped exactly like the rest of the platform (NR-6: reuse patterns, don't invent).

Security note: ``UserRecord`` carries **no secret material** (no password hash, no
salt). Credentials live only inside the auth credential store. This keeps user
records, versions, and reports deterministic and free of secrets.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    APPLICATION_DOMAIN_VERSION, APPLICATION_AUTH_VERSION, APPLICATION_USERS_VERSION,
    APPLICATION_WORKFLOW_VERSION, APPLICATION_API_VERSION, APPLICATION_REGISTRY_VERSION,
    APPLICATION_VALIDATION_VERSION, DETERMINISTIC_EPOCH,
)


def _sorted_str_tuple(values) -> tuple[str, ...]:
    return tuple(sorted({str(v) for v in values}))


# =============================================================================
# Closed vocabularies (no free-form states)
# =============================================================================
class UserRole(str, Enum):
    """The closed set of application roles (authorization is role-based)."""

    ADMIN = "admin"
    CLINICIAN = "clinician"
    RESEARCHER = "researcher"
    VIEWER = "viewer"


class UserStatus(str, Enum):
    """The standing of a user account."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DEACTIVATED = "deactivated"


class SessionStatus(str, Enum):
    """The standing of an authentication session."""

    ACTIVE = "active"
    REVOKED = "revoked"


class UploadStatus(str, Enum):
    """The standing of an uploaded EEG file (application-level receipt)."""

    RECEIVED = "received"
    CONSUMED = "consumed"          # used by a completed analysis
    REJECTED = "rejected"


class WorkflowStage(str, Enum):
    """The ordered stages of the EEG application workflow (closed)."""

    UPLOAD = "upload"
    VALIDATE = "validate"
    PROCESS = "process"
    FEATURES = "features"
    PREDICT = "predict"
    CONFIDENCE = "confidence"
    EXPLANATION = "explanation"


class WorkflowStatus(str, Enum):
    """The standing of a workflow run (deterministic; no in-between persistence)."""

    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisStatus(str, Enum):
    """The standing of an analysis result."""

    GENERATED = "generated"
    FAILED = "failed"


class RequestStatus(str, Enum):
    """The standing of an API request after validation."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ResponseStatus(str, Enum):
    """The closed set of structured API response statuses."""

    OK = "ok"
    CREATED = "created"
    BAD_REQUEST = "bad_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    ERROR = "error"

    @property
    def is_success(self) -> bool:
        return self in (ResponseStatus.OK, ResponseStatus.CREATED)


class ApiOperation(str, Enum):
    """The closed set of versioned API operations this phase exposes."""

    REGISTER_USER = "register_user"
    LOGIN = "login"
    LOGOUT = "logout"
    UPLOAD_EEG = "upload_eeg"
    LIST_EEG = "list_eeg"
    RETRIEVE_EEG = "retrieve_eeg"
    START_ANALYSIS = "start_analysis"
    RETRIEVE_PREDICTION = "retrieve_prediction"
    RETRIEVE_CONFIDENCE = "retrieve_confidence"
    RETRIEVE_EXPLANATION = "retrieve_explanation"
    LIST_ANALYSIS_HISTORY = "list_analysis_history"
    LIST_REPORTS = "list_reports"


class EntityKind(str, Enum):
    """The closed set of application entity kinds tracked by the registry."""

    USER = "user"
    SESSION = "session"
    UPLOAD = "upload"
    REQUEST = "request"
    RESPONSE = "response"
    WORKFLOW = "workflow"
    ANALYSIS = "analysis"
    API = "api"


# =============================================================================
# Versioning projection (content-addressed, chained — mirrors PredictionVersion)
# =============================================================================
@dataclass(frozen=True)
class BackendVersion:
    """A content-addressed application-entity version (chained like other phases)."""

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
# Identity projections
# =============================================================================
@dataclass(frozen=True)
class UserIdentity:
    """A user identity, content-addressed from its username. Never filename-derived."""

    user_id: str
    username: str
    identity_version: str
    domain_version: str = APPLICATION_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {"user_id": self.user_id, "username": self.username,
                "identity_version": self.identity_version, "domain_version": self.domain_version}


# =============================================================================
# User record (NO secret material)
# =============================================================================
@dataclass(frozen=True)
class UserRecord:
    """An **immutable** user account record (frozen). Carries no password/secret.

    Updates produce a new ``UserRecord`` at a new chained version (the service
    replaces the stored record), so history is reconstructable from the audit log.
    """

    identity: UserIdentity
    roles: tuple[UserRole, ...]
    status: UserStatus
    metadata: dict
    version: BackendVersion
    owner: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    users_version: str = APPLICATION_USERS_VERSION

    @property
    def user_id(self) -> str:
        return self.identity.user_id

    @property
    def username(self) -> str:
        return self.identity.username

    def has_role(self, role: UserRole) -> bool:
        return role in self.roles

    @staticmethod
    def state_signature_of(*, identity, roles, status, metadata) -> str:
        return hash_obj({
            "user_id": identity.user_id, "username": identity.username,
            "roles": sorted(r.value for r in roles), "status": status.value,
            "metadata": dict(sorted(metadata.items()))})

    def state_signature(self) -> str:
        return self.state_signature_of(identity=self.identity, roles=self.roles,
                                       status=self.status, metadata=self.metadata)

    def to_dict(self) -> dict:
        return {
            "identity": self.identity.to_dict(), "user_id": self.user_id, "username": self.username,
            "roles": sorted(r.value for r in self.roles), "status": self.status.value,
            "metadata": dict(sorted(self.metadata.items())), "version": self.version.to_dict(),
            "owner": self.owner, "created_at": self.created_at, "lineage_id": self.lineage_id,
            "audit_head": self.audit_head, "users_version": self.users_version,
            "state_signature": self.state_signature(),
        }


# =============================================================================
# Session record (stores only a token *fingerprint*, never the raw token)
# =============================================================================
@dataclass(frozen=True)
class SessionRecord:
    """An **immutable** session record. The raw token is returned to the caller once
    at login and is never stored — only ``token_fingerprint`` (a hash) is persisted."""

    session_id: str
    user_id: str
    token_fingerprint: str
    status: SessionStatus
    version: BackendVersion
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    auth_version: str = APPLICATION_AUTH_VERSION

    @staticmethod
    def state_signature_of(*, session_id, user_id, token_fingerprint, status) -> str:
        return hash_obj({"session_id": session_id, "user_id": user_id,
                         "token_fingerprint": token_fingerprint, "status": status.value})

    def state_signature(self) -> str:
        return self.state_signature_of(session_id=self.session_id, user_id=self.user_id,
                                       token_fingerprint=self.token_fingerprint, status=self.status)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id, "user_id": self.user_id,
            "token_fingerprint": self.token_fingerprint, "status": self.status.value,
            "version": self.version.to_dict(), "created_at": self.created_at,
            "lineage_id": self.lineage_id, "audit_head": self.audit_head,
            "auth_version": self.auth_version, "state_signature": self.state_signature(),
        }


# =============================================================================
# Upload record (application-level receipt of a real EEG file)
# =============================================================================
@dataclass(frozen=True)
class UploadRecord:
    """An **immutable** record of an uploaded EEG file (content-addressed by bytes)."""

    upload_id: str
    user_id: str
    filename: str
    content_fingerprint: str
    size_bytes: int
    status: UploadStatus
    stored_reference: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    domain_version: str = APPLICATION_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {
            "upload_id": self.upload_id, "user_id": self.user_id, "filename": self.filename,
            "content_fingerprint": self.content_fingerprint, "size_bytes": self.size_bytes,
            "status": self.status.value, "stored_reference": self.stored_reference,
            "created_at": self.created_at, "lineage_id": self.lineage_id,
            "audit_head": self.audit_head, "domain_version": self.domain_version,
        }


# =============================================================================
# Request / response records (API audit trail)
# =============================================================================
@dataclass(frozen=True)
class RequestRecord:
    """An **immutable** record of an inbound API request (params content-addressed)."""

    request_id: str
    operation: ApiOperation
    api_version: str
    user_id: Optional[str]
    session_id: Optional[str]
    params_fingerprint: str
    status: RequestStatus
    created_at: str = DETERMINISTIC_EPOCH
    domain_version: str = APPLICATION_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id, "operation": self.operation.value,
            "api_version": self.api_version, "user_id": self.user_id, "session_id": self.session_id,
            "params_fingerprint": self.params_fingerprint, "status": self.status.value,
            "created_at": self.created_at, "domain_version": self.domain_version,
        }


@dataclass(frozen=True)
class ResponseRecord:
    """An **immutable** record of an API response (body content-addressed)."""

    response_id: str
    request_id: str
    status: ResponseStatus
    body_fingerprint: str
    error_code: Optional[str] = None
    created_at: str = DETERMINISTIC_EPOCH
    domain_version: str = APPLICATION_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {
            "response_id": self.response_id, "request_id": self.request_id,
            "status": self.status.value, "body_fingerprint": self.body_fingerprint,
            "error_code": self.error_code, "created_at": self.created_at,
            "domain_version": self.domain_version,
        }


# =============================================================================
# Workflow record (an orchestration run of the EEG pipeline)
# =============================================================================
@dataclass(frozen=True)
class WorkflowRecord:
    """An **immutable** record of one EEG application-workflow run.

    Holds the ids of every artifact the orchestration produced through the reused
    P1-P5 services, the ordered stages it executed, its status, version, lineage join
    node, and audit head. It duplicates no business logic — only references."""

    workflow_id: str
    upload_id: str
    user_id: str
    case_id: str
    patient_id: str
    eeg_asset_id: str
    processed_id: str
    feature_asset_id: str
    model_id: str
    prediction_id: str
    stages: tuple[WorkflowStage, ...]
    status: WorkflowStatus
    version: BackendVersion
    owner: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    dependencies: tuple[str, ...] = ()
    workflow_version: str = APPLICATION_WORKFLOW_VERSION

    @staticmethod
    def state_signature_of(*, workflow_id, upload_id, user_id, case_id, patient_id, eeg_asset_id,
                           processed_id, feature_asset_id, model_id, prediction_id, stages, status,
                           dependencies) -> str:
        return hash_obj({
            "workflow_id": workflow_id, "upload_id": upload_id, "user_id": user_id,
            "case_id": case_id, "patient_id": patient_id, "eeg_asset_id": eeg_asset_id,
            "processed_id": processed_id, "feature_asset_id": feature_asset_id, "model_id": model_id,
            "prediction_id": prediction_id, "stages": [s.value for s in stages],
            "status": status.value, "dependencies": list(dependencies)})

    def state_signature(self) -> str:
        return self.state_signature_of(
            workflow_id=self.workflow_id, upload_id=self.upload_id, user_id=self.user_id,
            case_id=self.case_id, patient_id=self.patient_id, eeg_asset_id=self.eeg_asset_id,
            processed_id=self.processed_id, feature_asset_id=self.feature_asset_id,
            model_id=self.model_id, prediction_id=self.prediction_id, stages=self.stages,
            status=self.status, dependencies=self.dependencies)

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id, "upload_id": self.upload_id, "user_id": self.user_id,
            "case_id": self.case_id, "patient_id": self.patient_id, "eeg_asset_id": self.eeg_asset_id,
            "processed_id": self.processed_id, "feature_asset_id": self.feature_asset_id,
            "model_id": self.model_id, "prediction_id": self.prediction_id,
            "stages": [s.value for s in self.stages], "status": self.status.value,
            "version": self.version.to_dict(), "owner": self.owner, "created_at": self.created_at,
            "lineage_id": self.lineage_id, "audit_head": self.audit_head,
            "dependencies": list(self.dependencies), "workflow_version": self.workflow_version,
            "state_signature": self.state_signature(),
        }


# =============================================================================
# Analysis record (the clinical-result summary for retrieval endpoints)
# =============================================================================
@dataclass(frozen=True)
class AnalysisRecord:
    """An **immutable** summary of one analysis result (references the prediction asset).

    Carries only the *summary* fields needed to list/retrieve a result; the full
    prediction / confidence / calibration / explanation come from the reused P5
    inference asset + its report builders (no duplication)."""

    analysis_id: str
    workflow_id: str
    user_id: str
    prediction_id: str
    case_id: str
    patient_id: str
    predicted_class: int
    predicted_label: str
    confidence_level: str
    calibration_quality: str
    status: AnalysisStatus
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    domain_version: str = APPLICATION_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {
            "analysis_id": self.analysis_id, "workflow_id": self.workflow_id, "user_id": self.user_id,
            "prediction_id": self.prediction_id, "case_id": self.case_id, "patient_id": self.patient_id,
            "predicted_class": self.predicted_class, "predicted_label": self.predicted_label,
            "confidence_level": self.confidence_level, "calibration_quality": self.calibration_quality,
            "status": self.status.value, "created_at": self.created_at, "lineage_id": self.lineage_id,
            "domain_version": self.domain_version,
        }


# =============================================================================
# API record (describes a versioned API contract — no undocumented operations)
# =============================================================================
@dataclass(frozen=True)
class APIRecord:
    """A description of the versioned API surface (its operations are a closed set)."""

    api_id: str
    name: str
    api_version: str
    operations: tuple[ApiOperation, ...]
    description: str
    domain_version: str = APPLICATION_API_VERSION

    def to_dict(self) -> dict:
        return {
            "api_id": self.api_id, "name": self.name, "api_version": self.api_version,
            "operations": [o.value for o in self.operations], "description": self.description,
            "domain_version": self.domain_version,
        }


# =============================================================================
# Registry / audit / lineage / validation projections
# =============================================================================
@dataclass
class BackendRegistryRecord:
    """A generic application registry entry (one per tracked entity).

    Every record references its audit head + lineage node so there can be no orphan
    records. Mutated only via the governed registry methods."""

    entity_kind: EntityKind
    entity_id: str
    status: str
    version: str
    owner: str
    creation_date: str
    audit_state: str
    lineage_id: str
    user_id: Optional[str] = None
    dependencies: tuple[str, ...] = ()
    registry_version: str = APPLICATION_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({
            "entity_kind": self.entity_kind.value, "entity_id": self.entity_id,
            "status": self.status, "version": self.version, "lineage_id": self.lineage_id,
            "audit_state": self.audit_state})

    def to_dict(self) -> dict:
        return {
            "entity_kind": self.entity_kind.value, "entity_id": self.entity_id,
            "status": self.status, "version": self.version, "owner": self.owner,
            "creation_date": self.creation_date, "audit_state": self.audit_state,
            "lineage_id": self.lineage_id, "user_id": self.user_id,
            "dependencies": list(self.dependencies), "registry_version": self.registry_version,
            "content_signature": self.content_signature(),
        }


@dataclass(frozen=True)
class BackendAuditRecord:
    """An immutable audit event in the hash-chained application audit log (shared log)."""

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
class BackendLineageRecord:
    """A projection of a shared lineage node attached to an application entity."""

    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


@dataclass(frozen=True)
class BackendValidationRecord:
    """A persisted projection of an application validation result."""

    validation_id: str
    ok: bool
    checks: tuple[tuple, ...]            # (name, passed, detail)
    validation_version: str = APPLICATION_VALIDATION_VERSION

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
