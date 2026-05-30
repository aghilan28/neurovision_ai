"""``backend/signal_processing/models`` — signal domain entities + closed vocabularies.

Pure data shapes (JSON-able, content-hashable). No I/O, no orchestration, no DSP.
See ``domain.py`` for the canonical definitions.
"""

from __future__ import annotations

from .domain import (
    # closed vocabularies
    SignalKind, FilterType, ArtifactType, RemovalMethod, ArtifactSeverity,
    QualityFindingSeverity, QualityGrade, ProcessedAssetStatus,
    # entities
    SignalIdentity, SignalRecord, ChannelQuality, SignalQualityFinding,
    SignalQualityRecord, SignalArtifactRecord, FilterConfig, SignalProcessingStep,
    SignalProcessingRecord, ProcessingHistory, ArtifactHistory, QualityHistory,
    ProcessedEEGStorageRecord, ProcessedEEGMetadata, SignalAuditRecord,
    SignalLineageRecord, SignalVersion, SignalRegistryRecord, ProcessedEEGRecord,
)

__all__ = [
    "SignalKind", "FilterType", "ArtifactType", "RemovalMethod", "ArtifactSeverity",
    "QualityFindingSeverity", "QualityGrade", "ProcessedAssetStatus",
    "SignalIdentity", "SignalRecord", "ChannelQuality", "SignalQualityFinding",
    "SignalQualityRecord", "SignalArtifactRecord", "FilterConfig", "SignalProcessingStep",
    "SignalProcessingRecord", "ProcessingHistory", "ArtifactHistory", "QualityHistory",
    "ProcessedEEGStorageRecord", "ProcessedEEGMetadata", "SignalAuditRecord",
    "SignalLineageRecord", "SignalVersion", "SignalRegistryRecord", "ProcessedEEGRecord",
]
