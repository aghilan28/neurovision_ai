"""``backend/application_backend`` — Application Backend Platform (Productization P6).

Exposes the platform's capabilities through governed **application services**,
transforming the internal P1-P5 platform into an application backend. The single use
case it delivers, end to end, is:

    authenticate -> upload EEG -> start analysis -> prediction + confidence +
    explanation -> retrieve results

…through in-process application backend services. **No frontend, deployment,
monitoring, or cloud infrastructure** (all out of scope for this phase).

Built strictly on P1-P5: it reuses ``CaseService`` + the EEG / signal / feature / model
/ inference services over a single shared ``ml.lineage.LineageTracker`` and the shared
``ImmutableAuditLog`` (no parallel pipelines, no parallel audit/lineage). The EEG
workflow orchestrates those services without duplicating their business logic; a
workflow's join lineage node parents both the upload node and the prediction node, so
one ``verify_chain`` proves
User -> Upload -> EEG -> Processed -> Feature -> Model -> Prediction.

Boundary (NR-8): part of the ``backend`` Application layer. Imports ``ml`` + sibling
``backend`` subsystems only; never imports ``frontend``. Authentication is local-only
(no social login / OAuth). Tests live in the repository-root ``tests/``; design notes
live in ``docs/``.
"""

from __future__ import annotations

from .version import (
    APPLICATION_BACKEND_VERSION, APPLICATION_DOMAIN_VERSION, APPLICATION_IDENTITY_VERSION,
    APPLICATION_AUTH_VERSION, APPLICATION_USERS_VERSION, APPLICATION_WORKFLOW_VERSION,
    APPLICATION_API_VERSION, APPLICATION_STORAGE_VERSION, APPLICATION_REGISTRY_VERSION,
    APPLICATION_AUDIT_VERSION, APPLICATION_LINEAGE_VERSION, APPLICATION_VALIDATION_VERSION,
    APPLICATION_REPORT_VERSION, API_V1,
)
from .models import (
    UserRole, UserStatus, SessionStatus, UploadStatus, WorkflowStage, WorkflowStatus,
    AnalysisStatus, RequestStatus, ResponseStatus, ApiOperation, EntityKind, BackendVersion,
    UserIdentity, UserRecord, SessionRecord, UploadRecord, RequestRecord, ResponseRecord,
    WorkflowRecord, AnalysisRecord, APIRecord, BackendRegistryRecord, BackendAuditRecord,
    BackendLineageRecord, BackendValidationRecord,
)
from .identity import (
    Identity, mint_identity, validate_identity, parse_identity, IdentityError,
)
from .audit import make_backend_audit_log, ImmutableAuditLog, AuditError
from .lineage import (
    make_user_lineage, make_session_lineage, make_upload_lineage, make_workflow_lineage,
    application_version_bundle, LineageTracker, LineageRecord,
)
from .registry import BackendRegistry, RegistryError
from .storage import (
    StorageError, CredentialStore, CredentialRecord, UploadByteStore,
)
from .users import UserService, UserManagementError
from .auth import (
    AuthService, AuthError, LoginResult, SecureEntropy, DeterministicEntropy,
    hash_password, verify_password, generate_token, token_fingerprint,
)
from .workflows import EegWorkflowService, ModelContext, WorkflowOutcome, WorkflowError
from .validation import RequestValidator, ApplicationIntegrityValidator
from .api import ApplicationAPI, ApiRequest, ApiResponse, describe_api
from .service import ApplicationBackendService, ApplicationBackendError

__all__ = [
    # versions
    "APPLICATION_BACKEND_VERSION", "APPLICATION_DOMAIN_VERSION", "APPLICATION_IDENTITY_VERSION",
    "APPLICATION_AUTH_VERSION", "APPLICATION_USERS_VERSION", "APPLICATION_WORKFLOW_VERSION",
    "APPLICATION_API_VERSION", "APPLICATION_STORAGE_VERSION", "APPLICATION_REGISTRY_VERSION",
    "APPLICATION_AUDIT_VERSION", "APPLICATION_LINEAGE_VERSION", "APPLICATION_VALIDATION_VERSION",
    "APPLICATION_REPORT_VERSION", "API_V1",
    # vocab + records
    "UserRole", "UserStatus", "SessionStatus", "UploadStatus", "WorkflowStage", "WorkflowStatus",
    "AnalysisStatus", "RequestStatus", "ResponseStatus", "ApiOperation", "EntityKind",
    "BackendVersion", "UserIdentity", "UserRecord", "SessionRecord", "UploadRecord", "RequestRecord",
    "ResponseRecord", "WorkflowRecord", "AnalysisRecord", "APIRecord", "BackendRegistryRecord",
    "BackendAuditRecord", "BackendLineageRecord", "BackendValidationRecord",
    # identity
    "Identity", "mint_identity", "validate_identity", "parse_identity", "IdentityError",
    # audit / lineage / registry / storage
    "make_backend_audit_log", "ImmutableAuditLog", "AuditError",
    "make_user_lineage", "make_session_lineage", "make_upload_lineage", "make_workflow_lineage",
    "application_version_bundle", "LineageTracker", "LineageRecord",
    "BackendRegistry", "RegistryError", "StorageError", "CredentialStore", "CredentialRecord",
    "UploadByteStore",
    # services
    "UserService", "UserManagementError",
    "AuthService", "AuthError", "LoginResult", "SecureEntropy", "DeterministicEntropy",
    "hash_password", "verify_password", "generate_token", "token_fingerprint",
    "EegWorkflowService", "ModelContext", "WorkflowOutcome", "WorkflowError",
    "RequestValidator", "ApplicationIntegrityValidator",
    "ApplicationAPI", "ApiRequest", "ApiResponse", "describe_api",
    "ApplicationBackendService", "ApplicationBackendError",
]
