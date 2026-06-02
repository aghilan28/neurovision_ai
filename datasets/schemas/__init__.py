"""Canonical schemas (data contracts) for the EEG data foundation (V1-P1).

These are the **formal, immutable shapes** every artifact in the data lifecycle
takes. Each dataclass is frozen (value-object semantics) and round-trips through
deterministic ``to_dict`` / ``from_dict`` so artifacts can be persisted, hashed,
and reproduced (AP-6, NR-10).

The eight governed data contracts (see ``datasets/contracts/``):

* :class:`~datasets.schemas.raw_eeg_file.RawEegFile`
* :class:`~datasets.schemas.validated_record.ValidatedEegRecord`
* :class:`~datasets.schemas.metadata_record.MetadataRecord`
* :class:`~datasets.schemas.dataset_entry.DatasetEntry`
* :class:`~datasets.schemas.patient_record.PatientRecord`
* :class:`~datasets.schemas.recording_session.RecordingSession`
* :class:`~datasets.schemas.manifest.DatasetManifest`
* :class:`~datasets.schemas.dataset_version.DatasetVersion`

Supporting structures: enums, channel descriptors, validation/quality reports,
and lineage records.
"""

from __future__ import annotations

from datasets.schemas.channels import ChannelDescriptor, ReferenceInfo
from datasets.schemas.dataset_entry import DatasetEntry
from datasets.schemas.dataset_version import DatasetVersion
from datasets.schemas.enums import (
    ChannelType,
    DatasetStatus,
    FileFormat,
    QualityState,
    RecordStatus,
    ValidationSeverity,
    ValidationStatus,
)
from datasets.schemas.lineage import LineageEdge, LineageRecord
from datasets.schemas.manifest import DatasetManifest, ManifestEntry
from datasets.schemas.metadata_record import Annotation, MetadataRecord, TechnicalMetadata
from datasets.schemas.patient_record import PatientRecord
from datasets.schemas.raw_eeg_file import RawEegFile
from datasets.schemas.recording_session import RecordingSession
from datasets.schemas.reports import (
    IntegrityResult,
    QualityReport,
    ValidationIssue,
    ValidationReport,
)
from datasets.schemas.validated_record import ValidatedEegRecord

__all__ = [
    "Annotation",
    "ChannelDescriptor",
    "ChannelType",
    "DatasetEntry",
    "DatasetManifest",
    "DatasetStatus",
    "DatasetVersion",
    "FileFormat",
    "IntegrityResult",
    "LineageEdge",
    "LineageRecord",
    "ManifestEntry",
    "MetadataRecord",
    "PatientRecord",
    "QualityReport",
    "QualityState",
    "RawEegFile",
    "RecordStatus",
    "RecordingSession",
    "ReferenceInfo",
    "TechnicalMetadata",
    "ValidationIssue",
    "ValidationReport",
    "ValidationSeverity",
    "ValidationStatus",
    "ValidatedEegRecord",
]
