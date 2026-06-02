"""EEG Foundation domain entities (Productization P1).

Pure data + ``to_dict`` + (where relevant) ``state_signature``. These are the
canonical, versioned shapes of a real EEG asset and everything attached to it. No I/O,
no orchestration, no signal processing — this module owns only the *shapes*.

Mandated entities: ``EEGIdentity`` (in ``identity``), ``EEGRecord``, ``EEGMetadata``,
``EEGSource``, ``EEGFormat``, ``EEGChannel``, ``EEGChannelSet``, ``EEGAnnotation``,
``EEGStorageRecord``, ``EEGAuditRecord``, ``EEGLineageRecord``, ``EEGRegistryRecord``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import EEG_DOMAIN_VERSION, EEG_REGISTRY_VERSION, DETERMINISTIC_EPOCH


# --- closed vocabularies ------------------------------------------------------
class EEGFormat:
    """The closed set of supported EEG container formats."""

    EDF = "EDF"
    EDF_PLUS = "EDF+"
    BDF = "BDF"
    BDF_PLUS = "BDF+"
    FIF = "FIF"
    SET = "SET"


SUPPORTED_FORMATS: frozenset[str] = frozenset({
    EEGFormat.EDF, EEGFormat.EDF_PLUS, EEGFormat.BDF, EEGFormat.BDF_PLUS,
    EEGFormat.FIF, EEGFormat.SET,
})

# file-extension hints (detection still inspects the bytes; extension is only a hint).
FORMAT_EXTENSIONS: dict[str, tuple[str, ...]] = {
    EEGFormat.EDF: (".edf",), EEGFormat.BDF: (".bdf",), EEGFormat.FIF: (".fif", ".fiff"),
    EEGFormat.SET: (".set",),
}


class EEGAssetStatus:
    """Lifecycle status of an EEG asset within the foundation (closed set)."""

    INGESTED = "ingested"
    VALIDATED = "validated"
    REJECTED = "rejected"
    STORED = "stored"
    REGISTERED = "registered"


# --- channel + annotation -----------------------------------------------------
@dataclass(frozen=True)
class EEGChannel:
    """One acquisition channel."""

    label: str
    index: int
    sampling_frequency: float
    physical_dimension: str = ""
    transducer: str = ""
    kind: str = "eeg"            # eeg | annotation | other (from the source where known)

    def to_dict(self) -> dict:
        return {"label": self.label, "index": self.index,
                "sampling_frequency": self.sampling_frequency,
                "physical_dimension": self.physical_dimension, "transducer": self.transducer,
                "kind": self.kind}


@dataclass(frozen=True)
class EEGChannelSet:
    """The ordered set of channels in a recording."""

    channels: tuple = ()                       # tuple[EEGChannel]

    @property
    def count(self) -> int:
        return len(self.channels)

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(c.label for c in self.channels)

    @property
    def signal_channels(self) -> tuple:
        return tuple(c for c in self.channels if c.kind != "annotation")

    def state_signature(self) -> str:
        return hash_obj({"channels": [c.to_dict() for c in self.channels]})

    def to_dict(self) -> dict:
        return {"count": self.count, "labels": list(self.labels),
                "channels": [c.to_dict() for c in self.channels]}


@dataclass(frozen=True)
class EEGAnnotation:
    """A time-stamped annotation/event extracted from the source file."""

    onset_seconds: float
    duration_seconds: float
    description: str

    def to_dict(self) -> dict:
        return {"onset_seconds": self.onset_seconds, "duration_seconds": self.duration_seconds,
                "description": self.description}


# --- source -------------------------------------------------------------------
@dataclass(frozen=True)
class EEGSource:
    """Where the asset came from: the original file reference + raw header echoes.

    ``original_filename`` is kept for traceability only; it is never used to derive
    identity (identity is content-addressed).
    """

    original_filename: str
    fmt: str
    subtype: str = ""                          # e.g. EDF+C / EDF+D / continuous
    file_size_bytes: int = 0
    source_patient_field: str = ""             # raw patient header field (as-found)
    source_recording_field: str = ""

    def to_dict(self) -> dict:
        return {"original_filename": self.original_filename, "format": self.fmt,
                "subtype": self.subtype, "file_size_bytes": self.file_size_bytes,
                "source_patient_field": self.source_patient_field,
                "source_recording_field": self.source_recording_field}


# --- normalized metadata ------------------------------------------------------
@dataclass(frozen=True)
class EEGMetadata:
    """Normalized, deterministic metadata — stored independently of the raw file."""

    recording_id: str
    fmt: str
    n_channels: int
    n_signal_channels: int
    sampling_frequency: float                  # representative (max signal-channel sfreq)
    sampling_frequencies: tuple = ()           # tuple[float] per channel
    duration_seconds: float = 0.0
    n_samples: int = 0
    channel_set: Optional[EEGChannelSet] = None
    annotation_count: int = 0
    annotation_types: tuple[str, ...] = ()
    recording_start: Optional[str] = None      # ISO-ish from the file (not wall-clock)
    patient_identifier: Optional[str] = None   # as present in the source (may be None)
    metadata_version: str = "eeg-metadata@1.0.0"

    def state_signature(self) -> str:
        return hash_obj({
            "recording_id": self.recording_id, "format": self.fmt,
            "n_channels": self.n_channels, "n_signal_channels": self.n_signal_channels,
            "sampling_frequency": self.sampling_frequency,
            "sampling_frequencies": list(self.sampling_frequencies),
            "duration_seconds": self.duration_seconds, "n_samples": self.n_samples,
            "channel_labels": list(self.channel_set.labels) if self.channel_set else [],
            "annotation_count": self.annotation_count,
            "annotation_types": list(self.annotation_types),
            "recording_start": self.recording_start,
            "patient_identifier": self.patient_identifier,
        })

    def to_dict(self) -> dict:
        return {
            "recording_id": self.recording_id, "format": self.fmt,
            "n_channels": self.n_channels, "n_signal_channels": self.n_signal_channels,
            "sampling_frequency": self.sampling_frequency,
            "sampling_frequencies": list(self.sampling_frequencies),
            "duration_seconds": self.duration_seconds, "n_samples": self.n_samples,
            "channel_set": self.channel_set.to_dict() if self.channel_set else None,
            "annotation_count": self.annotation_count,
            "annotation_types": list(self.annotation_types),
            "recording_start": self.recording_start,
            "patient_identifier": self.patient_identifier,
            "metadata_version": self.metadata_version,
        }


# --- storage ------------------------------------------------------------------
@dataclass(frozen=True)
class EEGStorageRecord:
    """A reference to the stored raw file (by reference; no cloud, no copy semantics)."""

    storage_id: str
    backend: str                               # "local"
    location: str                              # path / store key
    checksum_sha256: str
    fingerprint: str
    file_size_bytes: int
    version: str = ""
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None

    def state_signature(self) -> str:
        return hash_obj({"storage_id": self.storage_id, "backend": self.backend,
                         "checksum_sha256": self.checksum_sha256, "fingerprint": self.fingerprint,
                         "file_size_bytes": self.file_size_bytes})

    def to_dict(self) -> dict:
        return {"storage_id": self.storage_id, "backend": self.backend, "location": self.location,
                "checksum_sha256": self.checksum_sha256, "fingerprint": self.fingerprint,
                "file_size_bytes": self.file_size_bytes, "version": self.version,
                "created_at": self.created_at, "lineage_id": self.lineage_id}


# --- audit / lineage projections ---------------------------------------------
@dataclass(frozen=True)
class EEGAuditRecord:
    """An immutable audit event; field-compatible with the shared ImmutableAuditLog."""

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
class EEGLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


# --- registry record ----------------------------------------------------------
@dataclass
class EEGRegistryRecord:
    eeg_id: str
    fmt: str
    status: str
    validation_state: str                      # valid | invalid | not_validated
    storage_state: str                         # stored | not_stored
    metadata_state: str                        # extracted | missing
    version: str
    case_id: Optional[str]
    patient_id: Optional[str]
    lineage_id: str
    audit_state: str
    content_signature_value: str
    eeg_registry_version: str = EEG_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"eeg_id": self.eeg_id, "format": self.fmt, "version": self.version,
                         "lineage_id": self.lineage_id, "content": self.content_signature_value})

    def to_dict(self) -> dict:
        return {"eeg_id": self.eeg_id, "format": self.fmt, "status": self.status,
                "validation_state": self.validation_state, "storage_state": self.storage_state,
                "metadata_state": self.metadata_state, "version": self.version,
                "case_id": self.case_id, "patient_id": self.patient_id,
                "lineage_id": self.lineage_id, "audit_state": self.audit_state,
                "content_signature_value": self.content_signature_value,
                "eeg_registry_version": self.eeg_registry_version,
                "content_signature": self.content_signature()}


# --- the aggregate ------------------------------------------------------------
@dataclass(frozen=True)
class EEGRecord:
    """The EEG asset aggregate — a real EEG file made into a governed platform object."""

    eeg_id: str
    fmt: str
    source: EEGSource
    metadata: EEGMetadata
    storage: EEGStorageRecord
    status: str = EEGAssetStatus.INGESTED
    valid: bool = False
    validation_summary: dict = field(default_factory=dict)
    annotations: tuple = ()                    # tuple[EEGAnnotation]
    case_id: Optional[str] = None
    patient_id: Optional[str] = None
    version: str = ""
    previous_version: Optional[str] = None
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    created_at: str = DETERMINISTIC_EPOCH
    domain_version: str = EEG_DOMAIN_VERSION

    def version_previous(self) -> Optional[str]:
        return self.previous_version

    def state_signature(self) -> str:
        return hash_obj({
            "eeg_id": self.eeg_id, "format": self.fmt, "source": self.source.to_dict(),
            "metadata": self.metadata.state_signature(),
            "storage": self.storage.state_signature(), "status": self.status,
            "valid": self.valid, "validation_summary": self.validation_summary,
            "annotations": [a.to_dict() for a in self.annotations],
            "case_id": self.case_id, "patient_id": self.patient_id,
        })

    def to_dict(self) -> dict:
        return {
            "eeg_id": self.eeg_id, "format": self.fmt, "source": self.source.to_dict(),
            "metadata": self.metadata.to_dict(), "storage": self.storage.to_dict(),
            "status": self.status, "valid": self.valid,
            "validation_summary": self.validation_summary,
            "annotations": [a.to_dict() for a in self.annotations],
            "case_id": self.case_id, "patient_id": self.patient_id, "version": self.version,
            "lineage_id": self.lineage_id, "audit_state": self.audit_state,
            "created_at": self.created_at, "domain_version": self.domain_version,
            "state_signature": self.state_signature(),
        }
