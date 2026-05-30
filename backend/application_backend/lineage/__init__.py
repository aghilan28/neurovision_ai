"""``backend/application_backend/lineage`` — application lineage on the shared tracker (P6-J).

Builds content-addressed ``user``/``session``/``upload``/``workflow`` lineage nodes on
top of ``ml.lineage`` (the workflow node joins the upload + prediction branches) and
re-exports the shared ``LineageTracker``/``LineageRecord`` so application nodes live in
the same graph as every upstream node — giving User -> Upload -> ... -> Prediction
complete traceability with no parallel system.
"""

from __future__ import annotations

from .lineage import (
    application_version_bundle, make_user_lineage, make_session_lineage,
    make_upload_lineage, make_workflow_lineage,
)

from ml.lineage import LineageTracker, LineageRecord, make_lineage_record  # allowed: backend -> ml

__all__ = [
    "application_version_bundle", "make_user_lineage", "make_session_lineage",
    "make_upload_lineage", "make_workflow_lineage",
    "LineageTracker", "LineageRecord", "make_lineage_record",
]
