"""``backend/eeg_foundation/models`` — EEG domain entities + closed vocabularies.

Pure data shapes (JSON-able, content-hashable). No I/O, no orchestration, no
signal processing. See ``domain.py`` for the canonical definitions.
"""

from __future__ import annotations

from .domain import (
    # closed vocabularies
    EEGFormat,
    SUPPORTED_EXTENSIONS,
    EEGChannelType,
    EEGAssetStatus,
    EEGValidationSeverity,
    # entities
    EEGIdentity,
    EEGChannel,
    EEGChannelSet,
    EEGAnnotation,
    EEGSource,
    EEGMetadata,
    EEGValidationFinding,
    EEGValidationResult,
    EEGStorageRecord,
    EEGAuditRecord,
    EEGLineageRecord,
    EEGVersion,
    EEGRegistryRecord,
    EEGRecord,
)

__all__ = [
    "EEGFormat",
    "SUPPORTED_EXTENSIONS",
    "EEGChannelType",
    "EEGAssetStatus",
    "EEGValidationSeverity",
    "EEGIdentity",
    "EEGChannel",
    "EEGChannelSet",
    "EEGAnnotation",
    "EEGSource",
    "EEGMetadata",
    "EEGValidationFinding",
    "EEGValidationResult",
    "EEGStorageRecord",
    "EEGAuditRecord",
    "EEGLineageRecord",
    "EEGVersion",
    "EEGRegistryRecord",
    "EEGRecord",
]
