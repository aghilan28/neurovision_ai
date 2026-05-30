"""``backend/application_backend/models`` — application domain shapes + closed vocab (P6-B).

Pure, JSON-able, content-hashable records and closed enumerations. No I/O or
orchestration. Mirrors the platform domain-model pattern.
"""

from __future__ import annotations

from .domain import (
    # vocabularies
    UserRole, UserStatus, SessionStatus, UploadStatus, WorkflowStage, WorkflowStatus,
    AnalysisStatus, RequestStatus, ResponseStatus, ApiOperation, EntityKind,
    # versioning
    BackendVersion,
    # identities + records
    UserIdentity, UserRecord, SessionRecord, UploadRecord, RequestRecord, ResponseRecord,
    WorkflowRecord, AnalysisRecord, APIRecord,
    # projections
    BackendRegistryRecord, BackendAuditRecord, BackendLineageRecord, BackendValidationRecord,
)

__all__ = [
    "UserRole", "UserStatus", "SessionStatus", "UploadStatus", "WorkflowStage", "WorkflowStatus",
    "AnalysisStatus", "RequestStatus", "ResponseStatus", "ApiOperation", "EntityKind",
    "BackendVersion",
    "UserIdentity", "UserRecord", "SessionRecord", "UploadRecord", "RequestRecord", "ResponseRecord",
    "WorkflowRecord", "AnalysisRecord", "APIRecord",
    "BackendRegistryRecord", "BackendAuditRecord", "BackendLineageRecord", "BackendValidationRecord",
]
