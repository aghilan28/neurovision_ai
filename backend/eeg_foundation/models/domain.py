"""EEG Foundation domain entities + closed vocabularies (Productization P1).

These dataclasses are the canonical, versioned shapes of every EEG-foundation
record. They are pure data + ``to_dict`` (JSON-able, canonical) + ``signature``
(content hash) — no I/O, no orchestration, no signal processing. Identities are
minted by the identity system; ingestion parses real files; validation produces
structured findings; storage references raw bytes; audit events are appended to
the shared immutable audit log; lineage nodes are recorded via the shared lineage
tracker. This module owns only the *shapes* and the *closed vocabularies*.

Mirrors ``backend.clinical_cases.models.domain`` so the EEG layer is shaped exactly
like the rest of the platform (NR-6: reuse patterns, don't invent new ones).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    EEG_DOMAIN_VERSION,
    EEG_METADATA_VERSION,
    EEG_STORAGE_VERSION,
    EEG_REGISTRY_VERSION,
    EEG_VALIDATION_VERSION,
    DETERMINISTIC_EPOCH,
)


def _q(x: float) -> float:
    """Quantize a float to 6 decimals so derived numbers hash deterministically."""
    return round(float(x), 6)


# =============================================================================
# Closed vocabularies
# =============================================================================
class EEGFormat(str, Enum):
    """The closed set of EEG file formats this phase supports. No others."""

    EDF = "EDF"
    EDF_PLUS = "EDF+"
    BDF = "BDF"
    BDF_PLUS = "BDF+"
    FIF = "FIF"
    SET = "SET"

    @property
    def family(self) -> str:
        """The reader family: EDF/EDF+ -> 'EDF', BDF/BDF+ -> 'BDF', else self."""
        if self in (EEGFormat.EDF, EEGFormat.EDF_PLUS):
            return "EDF"
        if self in (EEGFormat.BDF, EEGFormat.BDF_PLUS):
            return "BDF"
        return self.value

    @property
    def is_plus(self) -> bool:
        """True for the annotation-bearing EDF+/BDF+ variants."""
        return self in (EEGFormat.EDF_PLUS, EEGFormat.BDF_PLUS)

    @classmethod
    def from_token(cls, token: str) -> "EEGFormat":
        """Parse a format token (e.g. 'edf+', 'EDF+') to a member, else raise."""
        norm = (token or "").strip().upper()
        for member in cls:
            if member.value == norm:
                return member
        raise ValueError(f"unsupported EEG format token {token!r}")


# Supported file extensions -> the format they *declare* (sniffing confirms it).
SUPPORTED_EXTENSIONS: dict[str, EEGFormat] = {
    ".edf": EEGFormat.EDF,   # EDF / EDF+ share an extension (reserved field disambiguates)
    ".bdf": EEGFormat.BDF,   # BDF / BDF+ share an extension
    ".fif": EEGFormat.FIF,
    ".set": EEGFormat.SET,
}


class EEGChannelType(str, Enum):
    """Closed channel-type vocabulary (normalized from the source reader)."""

    EEG = "eeg"
    EOG = "eog"
    ECG = "ecg"
    EMG = "emg"
    STIM = "stim"
    REF = "ref"
    BIO = "bio"
    SEEG = "seeg"
    ECOG = "ecog"
    RESP = "resp"
    MISC = "misc"
    UNKNOWN = "unknown"

    @classmethod
    def normalize(cls, token: str) -> "EEGChannelType":
        norm = (token or "").strip().lower()
        aliases = {
            "ref_meg": "ref", "eeg_ref": "ref", "temperature": "misc",
            "dbs": "seeg", "csd": "eeg", "gsr": "bio", "fnirs": "misc",
        }
        norm = aliases.get(norm, norm)
        for member in cls:
            if member.value == norm:
                return member
        return cls.UNKNOWN


class EEGAssetStatus(str, Enum):
    """The standing of an EEG asset after the ingest -> validate -> store path.

    Deliberately tiny (no workflow/lifecycle is built in this phase — that is
    forbidden future work). ``REGISTERED`` = accepted and traceable;
    ``QUARANTINED`` = registered but flagged because validation found a blocking
    (ERROR/CRITICAL) finding.
    """

    INGESTED = "ingested"
    REGISTERED = "registered"
    QUARANTINED = "quarantined"


class EEGValidationSeverity(str, Enum):
    """Ordered severity for a validation finding (CRITICAL/ERROR are blocking)."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @property
    def blocking(self) -> bool:
        return self in (EEGValidationSeverity.ERROR, EEGValidationSeverity.CRITICAL)


# =============================================================================
# Identity projection
# =============================================================================
@dataclass(frozen=True)
class EEGIdentity:
    """An EEG asset identity, derived (content-addressed) from a case identity.

    The asset id is a pure function of the case + the file's content fingerprint —
    never of the filename or folder (cardinal platform rule). The same bytes under
    the same case always yield the same ``asset_id``.
    """

    asset_id: str
    case_id: str
    identity_version: str
    domain_version: str = EEG_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {
            "asset_id": self.asset_id, "case_id": self.case_id,
            "identity_version": self.identity_version, "domain_version": self.domain_version,
        }


# =============================================================================
# Channels / annotations
# =============================================================================
@dataclass(frozen=True)
class EEGChannel:
    """A single channel as read from the source file."""

    label: str
    channel_type: EEGChannelType
    unit: str = ""
    sampling_frequency: float = 0.0

    def to_dict(self) -> dict:
        return {
            "label": self.label, "channel_type": self.channel_type.value,
            "unit": self.unit, "sampling_frequency": _q(self.sampling_frequency),
        }


@dataclass(frozen=True)
class EEGChannelSet:
    """The ordered set of channels + a derived layout summary."""

    channels: tuple[EEGChannel, ...] = ()

    @property
    def count(self) -> int:
        return len(self.channels)

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(c.label for c in self.channels)

    @property
    def layout(self) -> dict:
        """Histogram of channel types (deterministic ordering via sorted keys)."""
        hist: dict[str, int] = {}
        for c in self.channels:
            hist[c.channel_type.value] = hist.get(c.channel_type.value, 0) + 1
        return dict(sorted(hist.items()))

    def to_dict(self) -> dict:
        return {
            "count": self.count, "labels": list(self.labels),
            "layout": self.layout, "channels": [c.to_dict() for c in self.channels],
        }


@dataclass(frozen=True)
class EEGAnnotation:
    """A time-stamped annotation/event read from the source file."""

    onset_seconds: float
    duration_seconds: float
    description: str

    def to_dict(self) -> dict:
        return {
            "onset_seconds": _q(self.onset_seconds),
            "duration_seconds": _q(self.duration_seconds),
            "description": self.description,
        }


# =============================================================================
# Source / metadata
# =============================================================================
@dataclass(frozen=True)
class EEGSource:
    """Where the asset came from + how it was recognized.

    ``original_filename`` is the *basename only* (never a full path), and is never
    used to derive identity. ``detected_format`` is determined by inspecting the
    file's bytes; ``declared_format`` (if any) is what the extension/caller claimed.
    """

    original_filename: str
    detected_format: EEGFormat
    file_size_bytes: int
    source_checksum_sha256: str
    declared_format: Optional[EEGFormat] = None

    def to_dict(self) -> dict:
        return {
            "original_filename": self.original_filename,
            "detected_format": self.detected_format.value,
            "declared_format": self.declared_format.value if self.declared_format else None,
            "file_size_bytes": self.file_size_bytes,
            "source_checksum_sha256": self.source_checksum_sha256,
        }


@dataclass(frozen=True)
class EEGMetadata:
    """Normalized, deterministic EEG metadata — stored independently of raw bytes.

    Captures exactly what the directive requires: recording id, optional patient
    identifier, acquisition date, duration, sampling frequency, channel layout +
    labels, annotation count + types — plus the source-reported fields that were
    available. Never contains the raw signal; never depends on the filename.
    """

    recording_id: str
    eeg_format: EEGFormat
    duration_seconds: float
    sampling_frequency: float
    n_channels: int
    n_samples: int
    channel_labels: tuple[str, ...]
    channel_layout: dict
    n_annotations: int
    annotation_types: tuple[str, ...]
    patient_identifier: Optional[str] = None
    acquisition_date: Optional[str] = None
    highpass_hz: Optional[float] = None
    lowpass_hz: Optional[float] = None
    source_metadata: dict = field(default_factory=dict)
    metadata_version: str = EEG_METADATA_VERSION

    def signature(self) -> str:
        """Content hash of the normalized metadata (deterministic)."""
        return hash_obj(self._core())

    def _core(self) -> dict:
        return {
            "recording_id": self.recording_id,
            "eeg_format": self.eeg_format.value,
            "duration_seconds": _q(self.duration_seconds),
            "sampling_frequency": _q(self.sampling_frequency),
            "n_channels": self.n_channels,
            "n_samples": self.n_samples,
            "channel_labels": list(self.channel_labels),
            "channel_layout": dict(sorted(self.channel_layout.items())),
            "n_annotations": self.n_annotations,
            "annotation_types": list(self.annotation_types),
            "patient_identifier": self.patient_identifier,
            "acquisition_date": self.acquisition_date,
            "highpass_hz": None if self.highpass_hz is None else _q(self.highpass_hz),
            "lowpass_hz": None if self.lowpass_hz is None else _q(self.lowpass_hz),
        }

    def to_dict(self) -> dict:
        return {
            **self._core(),
            "source_metadata": dict(sorted(self.source_metadata.items())),
            "metadata_version": self.metadata_version,
            "metadata_signature": self.signature(),
        }


# =============================================================================
# Validation projections
# =============================================================================
@dataclass(frozen=True)
class EEGValidationFinding:
    """One structured validation finding (never an exception)."""

    code: str
    severity: EEGValidationSeverity
    message: str
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "code": self.code, "severity": self.severity.value,
            "message": self.message, "detail": dict(sorted(self.detail.items())),
        }


@dataclass(frozen=True)
class EEGValidationResult:
    """The structured outcome of validating one EEG input.

    ``ok`` is True iff there is no blocking (ERROR/CRITICAL) finding. Even a fully
    unreadable/corrupted file yields a result (with a CRITICAL finding) rather than
    raising — per the directive (P1-C: "Validation must return structured findings.
    Not exceptions.").
    """

    findings: tuple[EEGValidationFinding, ...] = ()
    validation_version: str = EEG_VALIDATION_VERSION

    @property
    def ok(self) -> bool:
        return not any(f.severity.blocking for f in self.findings)

    @property
    def has_errors(self) -> bool:
        return any(f.severity.blocking for f in self.findings)

    def counts(self) -> dict:
        out = {s.value: 0 for s in EEGValidationSeverity}
        for f in self.findings:
            out[f.severity.value] += 1
        return out

    def signature(self) -> str:
        return hash_obj({"findings": [f.to_dict() for f in self.findings]})

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "has_errors": self.has_errors,
            "n_findings": len(self.findings),
            "counts": self.counts(),
            "findings": [f.to_dict() for f in self.findings],
            "validation_version": self.validation_version,
            "validation_signature": self.signature(),
        }


# =============================================================================
# Storage projection
# =============================================================================
@dataclass(frozen=True)
class EEGStorageRecord:
    """A reference to stored raw bytes + integrity metadata (no cloud/S3/db).

    The raw EEG file is referenced (by a repository-relative path), checksummed
    (full sha256) and content-fingerprinted (short digest). ``version`` chains the
    storage state; ``created_at`` is non-hashed metadata.
    """

    storage_id: str
    raw_file_reference: str
    eeg_format: EEGFormat
    checksum_sha256: str
    content_fingerprint: str
    file_size_bytes: int
    version: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_refs: tuple[str, ...] = ()
    storage_version: str = EEG_STORAGE_VERSION

    def content_signature(self) -> str:
        return hash_obj({
            "storage_id": self.storage_id, "checksum_sha256": self.checksum_sha256,
            "content_fingerprint": self.content_fingerprint,
            "file_size_bytes": self.file_size_bytes, "eeg_format": self.eeg_format.value,
        })

    def to_dict(self) -> dict:
        return {
            "storage_id": self.storage_id,
            "raw_file_reference": self.raw_file_reference,
            "eeg_format": self.eeg_format.value,
            "checksum_sha256": self.checksum_sha256,
            "content_fingerprint": self.content_fingerprint,
            "file_size_bytes": self.file_size_bytes,
            "version": self.version,
            "created_at": self.created_at,
            "lineage_refs": list(self.lineage_refs),
            "storage_version": self.storage_version,
            "content_signature": self.content_signature(),
        }


# =============================================================================
# Audit / lineage projections
# =============================================================================
@dataclass(frozen=True)
class EEGAuditRecord:
    """An immutable audit event in the hash-chained EEG audit log.

    Field shape matches ``CaseAuditRecord`` so the shared ``ImmutableAuditLog`` can
    drive it directly (NR-6: one tamper-evident audit implementation, no parallel
    audit system).
    """

    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {
            "seq": self.seq, "kind": self.kind, "payload": self.payload,
            "prev_hash": self.prev_hash, "event_hash": self.event_hash,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class EEGLineageRecord:
    """A projection of the shared lineage node attached to an EEG asset."""

    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


# =============================================================================
# Version projection
# =============================================================================
@dataclass(frozen=True)
class EEGVersion:
    """A content-addressed asset version (bumped on every governed mutation).

    Chains the current state signature with the previous version (like
    ``CaseVersion``) so even a logically-identical re-derivation gets a unique,
    monotonic, still-reproducible version.
    """

    version: str
    previous: Optional[str]
    reason: str
    created_at: str = DETERMINISTIC_EPOCH

    @staticmethod
    def compute(state_signature: str, previous: Optional[str]) -> str:
        return hash_obj({"state": state_signature, "previous": previous})

    def to_dict(self) -> dict:
        return {
            "version": self.version, "previous": self.previous,
            "reason": self.reason, "created_at": self.created_at,
        }


# =============================================================================
# Registry record
# =============================================================================
@dataclass
class EEGRegistryRecord:
    """The registry entry shape (mutated only via governed registry methods).

    Tracks everything the directive's registry must track: the asset, its format,
    status, validation/storage/metadata state, and its audit + lineage references.
    """

    asset_id: str
    case_id: str
    patient_id: str
    eeg_format: EEGFormat
    status: EEGAssetStatus
    validation_state: str          # "ok" | "has_errors"
    storage_state: str             # "stored" | "absent"
    metadata_state: str            # "extracted" | "absent"
    version: str
    owner: str
    creation_date: str
    audit_state: str               # audit-log head hash (tamper-evident)
    lineage_id: str
    dependencies: tuple[str, ...]
    eeg_registry_version: str = EEG_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({
            "asset_id": self.asset_id, "case_id": self.case_id, "patient_id": self.patient_id,
            "eeg_format": self.eeg_format.value, "status": self.status.value,
            "version": self.version, "lineage_id": self.lineage_id,
        })

    def to_dict(self) -> dict:
        return {
            "asset_id": self.asset_id, "case_id": self.case_id, "patient_id": self.patient_id,
            "eeg_format": self.eeg_format.value, "status": self.status.value,
            "validation_state": self.validation_state, "storage_state": self.storage_state,
            "metadata_state": self.metadata_state, "version": self.version, "owner": self.owner,
            "creation_date": self.creation_date, "audit_state": self.audit_state,
            "lineage_id": self.lineage_id, "dependencies": list(self.dependencies),
            "eeg_registry_version": self.eeg_registry_version,
            "content_signature": self.content_signature(),
        }


# =============================================================================
# The aggregate — the NeuroVision EEG asset
# =============================================================================
@dataclass
class EEGRecord:
    """The EEG asset aggregate — a permanent, versioned, auditable, lineage-tracked
    record of a *real* EEG file that entered the platform.

    It references its case + patient, the source it came from, its parsed channels
    and annotations, its normalized metadata, its storage reference, its validation
    result, its current status, version, owner, lineage node, and audit-log head.
    It carries no raw signal and no analytics (out of scope for this phase).
    """

    identity: EEGIdentity
    case_id: str
    patient_id: str
    source: EEGSource
    eeg_format: EEGFormat
    channel_set: EEGChannelSet
    annotations: tuple[EEGAnnotation, ...]
    metadata: EEGMetadata
    storage: EEGStorageRecord
    validation: EEGValidationResult
    status: EEGAssetStatus
    version: EEGVersion
    owner: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    dependencies: tuple[str, ...] = ()
    domain_version: str = EEG_DOMAIN_VERSION

    @property
    def asset_id(self) -> str:
        return self.identity.asset_id

    def state_signature(self) -> str:
        """Content hash of the asset's mutable state (basis of EEGVersion)."""
        return hash_obj({
            "asset_id": self.asset_id,
            "case_id": self.case_id,
            "patient_id": self.patient_id,
            "eeg_format": self.eeg_format.value,
            "source": self.source.to_dict(),
            "channel_set": self.channel_set.to_dict(),
            "annotations": [a.to_dict() for a in self.annotations],
            "metadata_signature": self.metadata.signature(),
            "storage_signature": self.storage.content_signature(),
            "validation_signature": self.validation.signature(),
            "status": self.status.value,
            "dependencies": list(self.dependencies),
        })

    def to_dict(self) -> dict:
        return {
            "domain_version": self.domain_version,
            "identity": self.identity.to_dict(),
            "case_id": self.case_id,
            "patient_id": self.patient_id,
            "eeg_format": self.eeg_format.value,
            "source": self.source.to_dict(),
            "channel_set": self.channel_set.to_dict(),
            "annotations": [a.to_dict() for a in self.annotations],
            "metadata": self.metadata.to_dict(),
            "storage": self.storage.to_dict(),
            "validation": self.validation.to_dict(),
            "status": self.status.value,
            "version": self.version.to_dict(),
            "owner": self.owner,
            "created_at": self.created_at,
            "lineage_id": self.lineage_id,
            "audit_head": self.audit_head,
            "dependencies": list(self.dependencies),
            "state_signature": self.state_signature(),
        }
