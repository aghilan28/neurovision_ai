"""``backend/application_platform`` — Real Product Application (Track 3).

Turns the model platform (P1-P10 + DRP-1..6 + Track 1 + Track 2) into a **usable product**:
a real **FastAPI** HTTP API + governed user workflows — upload a real EEG file, validate it,
run the analysis (validate -> metadata -> features -> select model -> inference), generate a
prediction (+ confidence + calibration + model + evidence), produce a report (JSON/HTML/PDF),
and score application readiness (NOT_READY / PARTIALLY_READY / READY_FOR_USERS).

It REUSES ``application_backend`` (which already orchestrates the reused P1-P5 upload ->
prediction workflow), the Track-1 ``dataset_acquisition`` recordings, the Track-2
``real_model_training`` candidates, the shared ``ml.lineage`` tracker, the shared
``ImmutableAuditLog``, ``ml.validation`` and ``ml.provenance``. It retrains no models and
modifies no datasets, Track 1, Track 2, persistence, security, or deployment. Boundary:
imports ``ml`` + sibling ``backend`` only; never ``frontend``.

The HTTP layer is built lazily via ``create_app`` so importing the package never requires
FastAPI to be installed (only the API submodule does).
"""

from __future__ import annotations

from .version import (
    API_V1, APP_API_VERSION, APP_AUDIT_VERSION, APP_DOMAIN_VERSION, APP_IDENTITY_VERSION,
    APP_LINEAGE_VERSION, APP_PREDICTION_VERSION, APP_READINESS_VERSION, APP_REGISTRY_VERSION,
    APP_REPORT_VERSION, APP_UPLOAD_VERSION, APP_VALIDATION_VERSION, APP_WORKFLOW_VERSION,
    APPLICATION_PLATFORM_VERSION, DEFAULT_ANALYSIS_SECONDS, DETERMINISTIC_EPOCH,
)
from .models import (
    AnalysisRecord, ApplicationReadinessClass, ApplicationRegistryRecord, DuplicateClass,
    EntityKind, PredictionRequestRecord, PredictionResultRecord, ReadinessDimension,
    ReadinessRecord, ReportFormat, ReportRecord, RequestStatus, UploadFormat, UploadRecord,
    UploadStatus, UserRequestRecord, ValidationRecord, WorkflowRecord, WorkflowStage,
    WorkflowStatus,
)
from .identity import mint
from .uploads import (
    DuplicateDecision, DuplicateDetector, UploadValidation, content_hash,
    prepare_bounded_segment, validate_eeg_bytes,
)
from .readiness import ApplicationReadinessEngine
from .validation import ApplicationIntegrityValidator
from .registry import ApplicationRegistry, RegistryError
from .audit import AuditError, ImmutableAuditLog, make_application_audit_log
from .schemas import ENTITY_CONTRACTS, validate_entity
from .service import AnalysisOutcome, ApplicationPlatformError, ApplicationPlatformService


def create_app(service: "ApplicationPlatformService"):
    """Build the FastAPI app around a hub (imported lazily so FastAPI is optional)."""
    from .api import create_app as _create_app

    return _create_app(service)


__all__ = [
    "APPLICATION_PLATFORM_VERSION", "API_V1", "APP_DOMAIN_VERSION", "APP_IDENTITY_VERSION",
    "APP_API_VERSION", "APP_WORKFLOW_VERSION", "APP_UPLOAD_VERSION", "APP_PREDICTION_VERSION",
    "APP_REPORT_VERSION", "APP_VALIDATION_VERSION", "APP_READINESS_VERSION", "APP_REGISTRY_VERSION",
    "APP_AUDIT_VERSION", "APP_LINEAGE_VERSION", "DEFAULT_ANALYSIS_SECONDS", "DETERMINISTIC_EPOCH",
    "AnalysisRecord", "ApplicationReadinessClass", "ApplicationRegistryRecord", "DuplicateClass",
    "EntityKind", "PredictionRequestRecord", "PredictionResultRecord", "ReadinessDimension",
    "ReadinessRecord", "ReportFormat", "ReportRecord", "RequestStatus", "UploadFormat",
    "UploadRecord", "UploadStatus", "UserRequestRecord", "ValidationRecord", "WorkflowRecord",
    "WorkflowStage", "WorkflowStatus",
    "mint", "UploadValidation", "prepare_bounded_segment", "validate_eeg_bytes",
    "DuplicateDecision", "DuplicateDetector", "content_hash",
    "ApplicationReadinessEngine", "ApplicationIntegrityValidator", "ApplicationRegistry",
    "RegistryError", "AuditError", "ImmutableAuditLog", "make_application_audit_log",
    "ENTITY_CONTRACTS", "validate_entity", "AnalysisOutcome", "ApplicationPlatformError",
    "ApplicationPlatformService", "create_app",
]
