"""``backend/application_backend/storage`` — local application storage (P6-H).

In-process stores for users, sessions, uploads, workflows, analyses, requests, and
responses (plus a private credential store and a content-addressed upload byte store).
Compatible with the platform's in-memory model; no cloud, database, or distributed
systems.
"""

from __future__ import annotations

from .stores import (
    StorageError, RecordStore, CredentialRecord, CredentialStore, UploadByteStore,
    make_user_store, make_session_store, make_upload_store, make_workflow_store,
    make_analysis_store, make_request_store, make_response_store, STORAGE_VERSION,
)

__all__ = [
    "StorageError", "RecordStore", "CredentialRecord", "CredentialStore", "UploadByteStore",
    "make_user_store", "make_session_store", "make_upload_store", "make_workflow_store",
    "make_analysis_store", "make_request_store", "make_response_store", "STORAGE_VERSION",
]
