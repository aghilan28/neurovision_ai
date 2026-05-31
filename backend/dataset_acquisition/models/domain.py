"""Real Dataset Platform domain entities + closed vocabularies (Track 1, T1-B).

Pure, JSON-able, content-hashable records and closed enumerations describing the
**real** external-EEG-dataset lifecycle: acquisition, local management, real-file
connection, structure validation, label verification, recording inventory, and
training readiness. No I/O and no orchestration live here — only the *shapes* and
the *closed vocabularies* (NR-6: reuse the platform domain-model shape).

These records describe datasets that physically exist on local disk (acquired from
public sources) — never synthetic placeholders. Identities are content-addressed
from real file checksums, so the same files always yield the same ids.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    ACQUISITION_DOMAIN_VERSION, ACQUISITION_INVENTORY_VERSION, ACQUISITION_LABELS_VERSION,
    ACQUISITION_READINESS_VERSION, ACQUISITION_REGISTRY_VERSION, ACQUISITION_SOURCES_VERSION,
    ACQUISITION_STORAGE_VERSION, ACQUISITION_VALIDATION_VERSION, DETERMINISTIC_EPOCH,
)


def _q(x: float) -> float:
    """Quantize a float to 6 decimals so derived numbers hash deterministically."""
    return round(float(x), 6)


# =============================================================================
# Closed vocabularies
# =============================================================================
class DatasetSource(str, Enum):
    """The closed set of external EEG corpora Track 1 can acquire / manage."""

    CHB_MIT = "chb_mit"
    TUH_EEG = "tuh_eeg"
    TEMPLE_EEG = "temple_eeg"
    SIENA_SCALP = "siena_scalp"
    BONN = "bonn"
    OTHER = "other"


class AccessRequirement(str, Enum):
    """How a corpus may be obtained (drives auto-download policy).

    ``OPEN`` corpora can be downloaded automatically; ``REGISTRATION_REQUIRED`` /
    ``RESTRICTED`` corpora must NOT be auto-downloaded (an account / signed data-use
    agreement is required), so Track 1 only reports their acquisition plan.
    """

    OPEN = "open"
    REGISTRATION_REQUIRED = "registration_required"
    RESTRICTED = "restricted"


class AvailabilityState(str, Enum):
    """The actual local state of a dataset / file on disk (Dataset Availability Tracker)."""

    UNAVAILABLE = "unavailable"
    DOWNLOADING = "downloading"
    PARTIALLY_DOWNLOADED = "partially_downloaded"
    DOWNLOADED = "downloaded"
    CORRUPTED = "corrupted"
    VERIFIED = "verified"
    READY = "ready"


class RecordingFormat(str, Enum):
    EDF = "edf"
    EDF_PLUS = "edf_plus"
    BDF = "bdf"
    BDF_PLUS = "bdf_plus"
    FIF = "fif"
    SET = "set"
    ASCII = "ascii"
    OTHER = "other"


class LabelScheme(str, Enum):
    """The closed set of real label schemes Track 1 understands."""

    CHB_MIT_SEIZURE = "chb_mit_seizure"       # per-recording seizure / background + intervals
    TUH_EVENT = "tuh_event"                   # TUH term-based events (when available)
    BONN_CLASS = "bonn_class"                 # Bonn set membership (Z/O/N/F/S)
    NONE = "none"                             # no labels available


class LabelValue(str, Enum):
    """Closed label vocabulary for the seizure-detection task (CHB-MIT/TUH/Siena)."""

    SEIZURE = "seizure"
    BACKGROUND = "background"
    UNKNOWN = "unknown"


class ValidationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @property
    def blocking(self) -> bool:
        return self in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)


class TrainingReadinessClass(str, Enum):
    """Track 1 readiness classification (extends DRP-1 with READY_FOR_TRAINING)."""

    NOT_READY = "NOT_READY"
    PARTIALLY_READY = "PARTIALLY_READY"
    READY_FOR_TRAINING = "READY_FOR_TRAINING"


class EntityKind(str, Enum):
    SOURCE = "dataset_source"
    DATASET = "real_dataset"
    PATIENT = "dataset_patient"
    SESSION = "dataset_session"
    RECORDING = "dataset_recording"
    LABEL = "dataset_label"
    REGISTRY = "dataset_registry"


# =============================================================================
# T1-A — Acquisition source specification + report
# =============================================================================
@dataclass(frozen=True)
class AcquisitionSourceSpec:
    """The acquisition plan for one corpus (official source / mechanism / access / …)."""

    source: DatasetSource
    display_name: str
    official_source: str
    download_mechanism: str
    access_requirement: AccessRequirement
    license_name: str
    storage_requirements: str
    directory_structure: str
    expected_labels: str
    expected_metadata: str
    base_url: Optional[str] = None
    sample_files: tuple = ()                 # (relative_path, ...) the minimal subset to acquire
    auto_downloadable: bool = False
    attribution: str = ""
    sources_version: str = ACQUISITION_SOURCES_VERSION

    def to_dict(self) -> dict:
        return {"source": self.source.value, "display_name": self.display_name,
                "official_source": self.official_source,
                "download_mechanism": self.download_mechanism,
                "access_requirement": self.access_requirement.value,
                "license_name": self.license_name,
                "storage_requirements": self.storage_requirements,
                "directory_structure": self.directory_structure,
                "expected_labels": self.expected_labels,
                "expected_metadata": self.expected_metadata, "base_url": self.base_url,
                "sample_files": list(self.sample_files), "auto_downloadable": self.auto_downloadable,
                "attribution": self.attribution, "sources_version": self.sources_version}


@dataclass(frozen=True)
class AcquisitionItem:
    """The acquisition outcome for one file (planned / fetched / skipped / failed)."""

    relative_path: str
    url: Optional[str]
    state: AvailabilityState
    size_bytes: int = 0
    checksum_sha256: str = ""
    note: str = ""

    def to_dict(self) -> dict:
        return {"relative_path": self.relative_path, "url": self.url, "state": self.state.value,
                "size_bytes": self.size_bytes, "checksum_sha256": self.checksum_sha256,
                "note": self.note}


@dataclass(frozen=True)
class AcquisitionRecord:
    """The result of attempting to acquire (a subset of) a corpus."""

    source: DatasetSource
    spec_signature: str
    attempted: bool
    access_requirement: AccessRequirement
    items: tuple                              # (AcquisitionItem, ...)
    local_root: Optional[str] = None
    note: str = ""

    @property
    def n_acquired(self) -> int:
        return sum(1 for i in self.items
                   if i.state in (AvailabilityState.DOWNLOADED, AvailabilityState.VERIFIED,
                                  AvailabilityState.READY))

    def to_dict(self) -> dict:
        return {"source": self.source.value, "spec_signature": self.spec_signature,
                "attempted": self.attempted, "access_requirement": self.access_requirement.value,
                "n_items": len(self.items), "n_acquired": self.n_acquired,
                "local_root": self.local_root, "note": self.note,
                "items": [i.to_dict() for i in self.items]}


# =============================================================================
# T1-B — Local file / availability records
# =============================================================================
@dataclass(frozen=True)
class LocalFileRecord:
    """A real file present on local disk + its integrity facts."""

    relative_path: str
    absolute_path: str
    size_bytes: int
    checksum_sha256: str
    state: AvailabilityState
    storage_version: str = ACQUISITION_STORAGE_VERSION

    def to_dict(self) -> dict:
        return {"relative_path": self.relative_path, "absolute_path": self.absolute_path,
                "size_bytes": self.size_bytes, "checksum_sha256": self.checksum_sha256,
                "state": self.state.value, "storage_version": self.storage_version}


@dataclass(frozen=True)
class AvailabilityRecord:
    """The tracked availability of one dataset on disk (Dataset Availability Tracker)."""

    source: DatasetSource
    local_root: str
    state: AvailabilityState
    n_files: int
    n_verified: int
    total_bytes: int
    expected_files: tuple = ()
    missing_files: tuple = ()
    corrupted_files: tuple = ()

    def to_dict(self) -> dict:
        return {"source": self.source.value, "local_root": self.local_root,
                "state": self.state.value, "n_files": self.n_files, "n_verified": self.n_verified,
                "total_bytes": self.total_bytes, "expected_files": list(self.expected_files),
                "missing_files": list(self.missing_files),
                "corrupted_files": list(self.corrupted_files)}


# =============================================================================
# T1-C — Patient / session / recording / label records (from ACTUAL files)
# =============================================================================
@dataclass(frozen=True)
class RecordingRecord:
    """A single real recording read from an actual file via the eeg_foundation reader."""

    recording_id: str
    patient_id: str
    session_id: str
    relative_path: str
    fmt: RecordingFormat
    parse_ok: bool
    sampling_frequency: float
    duration_seconds: float
    n_samples: int
    n_channels: int
    channel_labels: tuple
    n_annotations: int
    checksum_sha256: str
    file_size_bytes: int
    label_id: Optional[str] = None
    error: Optional[str] = None
    domain_version: str = ACQUISITION_DOMAIN_VERSION

    def signature(self) -> str:
        return hash_obj({"recording_id": self.recording_id, "checksum": self.checksum_sha256,
                         "sfreq": _q(self.sampling_frequency), "n_samples": self.n_samples,
                         "n_channels": self.n_channels, "channels": list(self.channel_labels),
                         "parse_ok": self.parse_ok})

    def to_dict(self) -> dict:
        return {"recording_id": self.recording_id, "patient_id": self.patient_id,
                "session_id": self.session_id, "relative_path": self.relative_path,
                "format": self.fmt.value, "parse_ok": self.parse_ok,
                "sampling_frequency": _q(self.sampling_frequency),
                "duration_seconds": _q(self.duration_seconds), "n_samples": self.n_samples,
                "n_channels": self.n_channels, "channel_labels": list(self.channel_labels),
                "n_annotations": self.n_annotations, "checksum_sha256": self.checksum_sha256,
                "file_size_bytes": self.file_size_bytes, "label_id": self.label_id,
                "error": self.error, "signature": self.signature()}


@dataclass(frozen=True)
class PatientRecord:
    patient_id: str
    patient_key: str
    source: DatasetSource
    n_recordings: int
    n_sessions: int
    recording_ids: tuple = ()

    def to_dict(self) -> dict:
        return {"patient_id": self.patient_id, "patient_key": self.patient_key,
                "source": self.source.value, "n_recordings": self.n_recordings,
                "n_sessions": self.n_sessions, "recording_ids": list(self.recording_ids)}


@dataclass(frozen=True)
class SeizureInterval:
    start_seconds: float
    end_seconds: float

    def to_dict(self) -> dict:
        return {"start_seconds": _q(self.start_seconds), "end_seconds": _q(self.end_seconds)}


@dataclass(frozen=True)
class LabelRecord:
    """A real label for one recording (derived from real annotations / summaries)."""

    label_id: str
    recording_id: str
    scheme: LabelScheme
    value: LabelValue
    n_events: int
    events: tuple = ()                        # (SeizureInterval, ...)
    source_reference: str = ""                # e.g. the summary file the label came from
    labels_version: str = ACQUISITION_LABELS_VERSION

    def signature(self) -> str:
        return hash_obj({"label_id": self.label_id, "recording_id": self.recording_id,
                         "scheme": self.scheme.value, "value": self.value.value,
                         "events": [e.to_dict() for e in self.events]})

    def to_dict(self) -> dict:
        return {"label_id": self.label_id, "recording_id": self.recording_id,
                "scheme": self.scheme.value, "value": self.value.value, "n_events": self.n_events,
                "events": [e.to_dict() for e in self.events],
                "source_reference": self.source_reference, "labels_version": self.labels_version,
                "signature": self.signature()}


# =============================================================================
# T1-D — Structure validation projection
# =============================================================================
@dataclass(frozen=True)
class ValidationFinding:
    check: str
    severity: ValidationSeverity
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict:
        return {"check": self.check, "severity": self.severity.value, "passed": self.passed,
                "detail": self.detail}


@dataclass(frozen=True)
class StructureValidationRecord:
    validation_id: str
    ok: bool
    findings: tuple                           # (ValidationFinding, ...)
    validation_version: str = ACQUISITION_VALIDATION_VERSION

    @property
    def n_checks(self) -> int:
        return len(self.findings)

    @property
    def n_blocking_failed(self) -> int:
        return sum(1 for f in self.findings if (not f.passed) and f.severity.blocking)

    def signature(self) -> str:
        return hash_obj({"ok": self.ok,
                         "findings": [[f.check, f.severity.value, f.passed] for f in self.findings]})

    def to_dict(self) -> dict:
        return {"validation_id": self.validation_id, "ok": self.ok, "n_checks": self.n_checks,
                "n_blocking_failed": self.n_blocking_failed,
                "findings": [f.to_dict() for f in self.findings],
                "validation_version": self.validation_version, "signature": self.signature()}


# =============================================================================
# T1-E — Label verification projection
# =============================================================================
@dataclass(frozen=True)
class LabelVerificationRecord:
    verification_id: str
    scheme: LabelScheme
    n_recordings: int
    n_labeled: int
    coverage: float
    consistent: bool
    n_classes: int
    classes: tuple
    class_distribution: dict
    n_missing: int
    n_corrupted: int
    n_unsupported: int
    findings: tuple = ()
    labels_version: str = ACQUISITION_LABELS_VERSION

    def to_dict(self) -> dict:
        return {"verification_id": self.verification_id, "scheme": self.scheme.value,
                "n_recordings": self.n_recordings, "n_labeled": self.n_labeled,
                "coverage": _q(self.coverage), "consistent": self.consistent,
                "n_classes": self.n_classes, "classes": list(self.classes),
                "class_distribution": dict(sorted(self.class_distribution.items())),
                "n_missing": self.n_missing, "n_corrupted": self.n_corrupted,
                "n_unsupported": self.n_unsupported, "findings": list(self.findings),
                "labels_version": self.labels_version}


# =============================================================================
# T1-F — Inventory projection
# =============================================================================
@dataclass(frozen=True)
class InventoryRecord:
    inventory_id: str
    source: DatasetSource
    n_patients: int
    n_sessions: int
    n_recordings: int
    n_labels: int
    n_channels_distribution: dict
    sampling_frequencies: tuple
    total_duration_seconds: float
    total_bytes: int
    label_distribution: dict
    inventory_version: str = ACQUISITION_INVENTORY_VERSION

    def to_dict(self) -> dict:
        return {"inventory_id": self.inventory_id, "source": self.source.value,
                "n_patients": self.n_patients, "n_sessions": self.n_sessions,
                "n_recordings": self.n_recordings, "n_labels": self.n_labels,
                "n_channels_distribution": dict(sorted(self.n_channels_distribution.items())),
                "sampling_frequencies": [_q(s) for s in self.sampling_frequencies],
                "total_duration_seconds": _q(self.total_duration_seconds),
                "total_bytes": self.total_bytes,
                "label_distribution": dict(sorted(self.label_distribution.items())),
                "inventory_version": self.inventory_version}


# =============================================================================
# T1-G — Readiness projection
# =============================================================================
@dataclass(frozen=True)
class TrainingReadinessRecord:
    readiness_id: str
    score: float
    classification: TrainingReadinessClass
    dimensions: dict
    findings: tuple
    readiness_version: str = ACQUISITION_READINESS_VERSION

    def to_dict(self) -> dict:
        return {"readiness_id": self.readiness_id, "score": _q(self.score),
                "classification": self.classification.value,
                "dimensions": dict(sorted(self.dimensions.items())),
                "findings": list(self.findings), "readiness_version": self.readiness_version}


# =============================================================================
# The aggregate — a real, locally-present dataset
# =============================================================================
@dataclass(frozen=True)
class RealDatasetRecord:
    """An immutable record of a **real** dataset that exists on local disk.

    Carries no recording arrays — only the governed metadata, the deterministic
    content fingerprint (over real file checksums + labels), cross-references to the
    availability / validation / label-verification / inventory / readiness
    projections, the lineage node, and the audit head.
    """

    dataset_id: str
    source: DatasetSource
    name: str
    local_root: str
    content_fingerprint: str
    n_patients: int
    n_recordings: int
    n_labels: int
    availability_state: AvailabilityState
    validation_id: Optional[str] = None
    label_verification_id: Optional[str] = None
    inventory_id: Optional[str] = None
    readiness_id: Optional[str] = None
    source_id: Optional[str] = None
    acquisition_signature: Optional[str] = None
    owner: str = "dataset-ops"
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    registry_lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    domain_version: str = ACQUISITION_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {"dataset_id": self.dataset_id, "source": self.source.value, "name": self.name,
                "local_root": self.local_root, "content_fingerprint": self.content_fingerprint,
                "n_patients": self.n_patients, "n_recordings": self.n_recordings,
                "n_labels": self.n_labels, "availability_state": self.availability_state.value,
                "validation_id": self.validation_id,
                "label_verification_id": self.label_verification_id,
                "inventory_id": self.inventory_id, "readiness_id": self.readiness_id,
                "source_id": self.source_id, "acquisition_signature": self.acquisition_signature,
                "owner": self.owner, "created_at": self.created_at, "lineage_id": self.lineage_id,
                "registry_lineage_id": self.registry_lineage_id, "audit_head": self.audit_head,
                "domain_version": self.domain_version}


# =============================================================================
# Registry / audit / lineage projections
# =============================================================================
@dataclass
class AcquisitionRegistryRecord:
    entity_kind: EntityKind
    entity_id: str
    status: str
    version: str
    owner: str
    creation_date: str
    audit_state: str
    lineage_id: str
    source: Optional[str] = None
    dependencies: tuple = ()
    registry_version: str = ACQUISITION_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"entity_kind": self.entity_kind.value, "entity_id": self.entity_id,
                         "status": self.status, "version": self.version,
                         "lineage_id": self.lineage_id, "audit_state": self.audit_state})

    def to_dict(self) -> dict:
        return {"entity_kind": self.entity_kind.value, "entity_id": self.entity_id,
                "status": self.status, "version": self.version, "owner": self.owner,
                "creation_date": self.creation_date, "audit_state": self.audit_state,
                "lineage_id": self.lineage_id, "source": self.source,
                "dependencies": list(self.dependencies), "registry_version": self.registry_version,
                "content_signature": self.content_signature()}


@dataclass(frozen=True)
class AcquisitionAuditRecord:
    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {"seq": self.seq, "kind": self.kind, "payload": self.payload,
                "prev_hash": self.prev_hash, "event_hash": self.event_hash,
                "created_at": self.created_at}


@dataclass(frozen=True)
class AcquisitionLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


__all__ = [
    "DatasetSource", "AccessRequirement", "AvailabilityState", "RecordingFormat", "LabelScheme",
    "LabelValue", "ValidationSeverity", "TrainingReadinessClass", "EntityKind",
    "AcquisitionSourceSpec", "AcquisitionItem", "AcquisitionRecord", "LocalFileRecord",
    "AvailabilityRecord", "RecordingRecord", "PatientRecord", "SeizureInterval", "LabelRecord",
    "ValidationFinding", "StructureValidationRecord", "LabelVerificationRecord", "InventoryRecord",
    "TrainingReadinessRecord", "RealDatasetRecord", "AcquisitionRegistryRecord",
    "AcquisitionAuditRecord", "AcquisitionLineageRecord",
]
