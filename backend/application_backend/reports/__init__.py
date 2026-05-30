"""``backend/application_backend/reports`` — reproducible application reports (P6-L).

Builders for the user, session, workflow, analysis, api, registry, audit, lineage, and
validation reports. Each is a deterministic, version-tagged JSON-able dict.
"""

from __future__ import annotations

from .reports import (
    build_user_report, build_session_report, build_workflow_report, build_analysis_report,
    build_api_report, build_registry_report, build_audit_report, build_lineage_report,
    build_validation_report,
)

__all__ = [
    "build_user_report", "build_session_report", "build_workflow_report", "build_analysis_report",
    "build_api_report", "build_registry_report", "build_audit_report", "build_lineage_report",
    "build_validation_report",
]
