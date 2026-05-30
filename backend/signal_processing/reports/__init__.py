"""``backend/signal_processing/reports`` — reproducible signal reports (P2-J).

Builders for the quality, artifact, filtering, processing, registry, audit, and
lineage reports. Each is a deterministic, version-tagged JSON-able dict.
"""

from __future__ import annotations

from .reports import (
    build_quality_report, build_artifact_report, build_filtering_report,
    build_processing_report, build_audit_report, build_lineage_report,
    build_registry_report,
)

__all__ = [
    "build_quality_report", "build_artifact_report", "build_filtering_report",
    "build_processing_report", "build_audit_report", "build_lineage_report",
    "build_registry_report",
]
