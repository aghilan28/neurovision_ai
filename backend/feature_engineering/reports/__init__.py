"""``backend/feature_engineering/reports`` — reproducible feature reports (P3-L).

Builders for the frequency, temporal, connectivity, spectral, topography, registry,
audit, lineage, and validation reports. Each is a deterministic, version-tagged
JSON-able dict.
"""

from __future__ import annotations

from .reports import (
    build_frequency_report, build_temporal_report, build_connectivity_report,
    build_spectral_report, build_topography_report, build_audit_report,
    build_lineage_report, build_validation_report, build_registry_report,
)

__all__ = [
    "build_frequency_report", "build_temporal_report", "build_connectivity_report",
    "build_spectral_report", "build_topography_report", "build_audit_report",
    "build_lineage_report", "build_validation_report", "build_registry_report",
]
