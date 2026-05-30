"""Signal Processing domain entities + closed vocabularies (Productization P2).

Pure data shapes (JSON-able, content-hashable) + ``to_dict`` + ``signature``. No
I/O, no orchestration, no actual DSP — this module owns only the *shapes* and the
*closed vocabularies* (no free-form states). The engines (filtering / quality /
artifacts / removal) and the service produce and consume these records.

Mirrors ``backend.eeg_foundation.models.domain`` so the signal layer is shaped
exactly like the rest of the platform (NR-6: reuse patterns, don't invent).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    SIGNAL_DOMAIN_VERSION, SIGNAL_QUALITY_VERSION, SIGNAL_ARTIFACT_VERSION,
    SIGNAL_PREPROCESSING_VERSION, SIGNAL_STORAGE_VERSION, SIGNAL_REGISTRY_VERSION,
    DETERMINISTIC_EPOCH,
)


def _q(x: float, n: int = 6) -> float:
    """Quantize a float so derived numbers hash deterministically."""
    return round(float(x), n)


# =============================================================================
# Closed vocabularies (no free-form states)
# =============================================================================
class SignalKind(str, Enum):
    """A signal is either the immutable raw recording or a processed derivative."""

    RAW = "raw"
    PROCESSED = "processed"


class FilterType(str, Enum):
    """The closed set of supported filter operations."""

    BANDPASS = "bandpass"
    HIGHPASS = "highpass"
    LOWPASS = "lowpass"
    NOTCH = "notch"
    REFERENCE = "reference"


class ArtifactType(str, Enum):
    """The closed set of detectable artifact classes."""

    EYE_BLINK = "eye_blink"
    EMG = "emg"
    MOVEMENT = "movement"
    POWERLINE = "powerline"
    CHANNEL_DROPOUT = "channel_dropout"
    FLAT_CHANNEL = "flat_channel"
    SATURATED_CHANNEL = "saturated_channel"


class RemovalMethod(str, Enum):
    """The closed set of artifact-removal / repair methods."""

    ICA = "ica"
    ADAPTIVE_FILTER = "adaptive_filter"
    INTERPOLATION = "interpolation"
    CHANNEL_REPAIR = "channel_repair"
    NOISE_SUPPRESSION = "noise_suppression"


class ArtifactSeverity(str, Enum):
    """Ordered artifact magnitude."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class QualityFindingSeverity(str, Enum):
    """Ordered severity for a quality finding (ERROR/CRITICAL are blocking)."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @property
    def blocking(self) -> bool:
        return self in (QualityFindingSeverity.ERROR, QualityFindingSeverity.CRITICAL)


class QualityGrade(str, Enum):
    """A closed grade band derived from the recording quality score."""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNUSABLE = "unusable"

    @classmethod
    def from_score(cls, score: float) -> "QualityGrade":
        if score >= 0.90:
            return cls.EXCELLENT
        if score >= 0.75:
            return cls.GOOD
        if score >= 0.55:
            return cls.FAIR
        if score >= 0.30:
            return cls.POOR
        return cls.UNUSABLE


class ProcessedAssetStatus(str, Enum):
    """The standing of a processed EEG asset (deliberately tiny; no workflow)."""

    PROCESSED = "processed"
    QUARANTINED = "quarantined"


# =============================================================================
# Identity projection
# =============================================================================
@dataclass(frozen=True)
class SignalIdentity:
    """A processed-EEG asset identity, derived (content-addressed) from a raw EEG
    asset id + the processing fingerprint. Never filename-derived."""

    processed_id: str
    eeg_asset_id: str
    identity_version: str
    domain_version: str = SIGNAL_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {
            "processed_id": self.processed_id, "eeg_asset_id": self.eeg_asset_id,
            "identity_version": self.identity_version, "domain_version": self.domain_version,
        }


# =============================================================================
# Signal descriptor (raw or processed)
# =============================================================================
@dataclass(frozen=True)
class SignalRecord:
    """A descriptor of a signal (raw or processed) — shape + a content fingerprint
    of the underlying samples. Carries no raw array (that lives in storage)."""

    signal_kind: SignalKind
    n_channels: int
    sampling_frequency: float
    n_samples: int
    channel_labels: tuple[str, ...]
    content_fingerprint: str

    @property
    def duration_seconds(self) -> float:
        return _q(self.n_samples / self.sampling_frequency) if self.sampling_frequency > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "signal_kind": self.signal_kind.value, "n_channels": self.n_channels,
            "sampling_frequency": _q(self.sampling_frequency), "n_samples": self.n_samples,
            "duration_seconds": self.duration_seconds,
            "channel_labels": list(self.channel_labels),
            "content_fingerprint": self.content_fingerprint,
        }


# =============================================================================
# Quality projections
# =============================================================================
@dataclass(frozen=True)
class ChannelQuality:
    """Per-channel quality metrics (all in [0,1] except noise_level which is RMS)."""

    label: str
    quality_score: float
    noise_level: float
    flatness: float
    saturation_fraction: float
    completeness: float
    stability: float

    def to_dict(self) -> dict:
        return {
            "label": self.label, "quality_score": _q(self.quality_score),
            "noise_level": _q(self.noise_level), "flatness": _q(self.flatness),
            "saturation_fraction": _q(self.saturation_fraction),
            "completeness": _q(self.completeness), "stability": _q(self.stability),
        }


@dataclass(frozen=True)
class SignalQualityFinding:
    """One structured quality finding (never an exception)."""

    code: str
    severity: QualityFindingSeverity
    message: str
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "code": self.code, "severity": self.severity.value, "message": self.message,
            "detail": dict(sorted(self.detail.items())),
        }


@dataclass(frozen=True)
class SignalQualityRecord:
    """The full quality assessment of a signal (raw or processed)."""

    quality_id: str
    eeg_asset_id: str
    signal_kind: SignalKind
    recording_quality_score: float
    noise_level: float
    signal_stability: float
    signal_completeness: float
    sampling_consistency: float
    grade: QualityGrade
    channel_qualities: tuple[ChannelQuality, ...]
    findings: tuple[SignalQualityFinding, ...]
    recommendations: tuple[str, ...]
    quality_version: str = SIGNAL_QUALITY_VERSION

    def signature(self) -> str:
        return hash_obj(self._core())

    def _core(self) -> dict:
        return {
            "eeg_asset_id": self.eeg_asset_id, "signal_kind": self.signal_kind.value,
            "recording_quality_score": _q(self.recording_quality_score),
            "noise_level": _q(self.noise_level), "signal_stability": _q(self.signal_stability),
            "signal_completeness": _q(self.signal_completeness),
            "sampling_consistency": _q(self.sampling_consistency), "grade": self.grade.value,
            "channel_qualities": [c.to_dict() for c in self.channel_qualities],
            "findings": [f.to_dict() for f in self.findings],
            "recommendations": list(self.recommendations),
        }

    def to_dict(self) -> dict:
        return {
            "quality_id": self.quality_id, **self._core(),
            "quality_version": self.quality_version, "quality_signature": self.signature(),
        }


# =============================================================================
# Artifact projection
# =============================================================================
@dataclass(frozen=True)
class SignalArtifactRecord:
    """A structured record of one detected artifact."""

    artifact_id: str
    artifact_type: ArtifactType
    severity: ArtifactSeverity
    confidence: float
    affected_channels: tuple[str, ...]
    onset_seconds: float
    duration_seconds: float
    detail: dict = field(default_factory=dict)
    artifact_version: str = SIGNAL_ARTIFACT_VERSION

    def signature(self) -> str:
        return hash_obj({
            "artifact_type": self.artifact_type.value, "severity": self.severity.value,
            "confidence": _q(self.confidence), "affected_channels": list(self.affected_channels),
            "onset_seconds": _q(self.onset_seconds), "duration_seconds": _q(self.duration_seconds),
        })

    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id, "artifact_type": self.artifact_type.value,
            "severity": self.severity.value, "confidence": _q(self.confidence),
            "affected_channels": list(self.affected_channels),
            "onset_seconds": _q(self.onset_seconds), "duration_seconds": _q(self.duration_seconds),
            "detail": dict(sorted(self.detail.items())), "artifact_version": self.artifact_version,
            "artifact_signature": self.signature(),
        }


# =============================================================================
# Filtering / processing projections
# =============================================================================
@dataclass(frozen=True)
class FilterConfig:
    """A tracked filter configuration (deterministic, reproducible)."""

    filter_type: FilterType
    params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"filter_type": self.filter_type.value, "params": dict(sorted(self.params.items()))}


@dataclass(frozen=True)
class SignalProcessingStep:
    """One ordered, deterministic processing operation + its before/after fingerprint."""

    order: int
    operation: str               # FilterType.value or RemovalMethod.value
    params: dict
    input_fingerprint: str
    output_fingerprint: str
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "order": self.order, "operation": self.operation,
            "params": dict(sorted(self.params.items())),
            "input_fingerprint": self.input_fingerprint,
            "output_fingerprint": self.output_fingerprint, "note": self.note,
        }


@dataclass(frozen=True)
class SignalProcessingRecord:
    """The full, ordered processing pipeline applied to a raw signal."""

    processing_id: str
    eeg_asset_id: str
    filter_configs: tuple[FilterConfig, ...]
    removal_methods: tuple[RemovalMethod, ...]
    steps: tuple[SignalProcessingStep, ...]
    input_fingerprint: str
    output_fingerprint: str
    processing_version: str = SIGNAL_PREPROCESSING_VERSION

    def signature(self) -> str:
        return hash_obj({
            "eeg_asset_id": self.eeg_asset_id,
            "filter_configs": [f.to_dict() for f in self.filter_configs],
            "removal_methods": [m.value for m in self.removal_methods],
            "steps": [s.to_dict() for s in self.steps],
            "input_fingerprint": self.input_fingerprint,
            "output_fingerprint": self.output_fingerprint,
        })

    def to_dict(self) -> dict:
        return {
            "processing_id": self.processing_id, "eeg_asset_id": self.eeg_asset_id,
            "filter_configs": [f.to_dict() for f in self.filter_configs],
            "removal_methods": [m.value for m in self.removal_methods],
            "steps": [s.to_dict() for s in self.steps],
            "input_fingerprint": self.input_fingerprint,
            "output_fingerprint": self.output_fingerprint,
            "processing_version": self.processing_version,
            "processing_signature": self.signature(),
        }


# =============================================================================
# Histories (P2-G)
# =============================================================================
@dataclass(frozen=True)
class ProcessingHistory:
    """Ordered record of every processing step applied (raw -> processed)."""

    steps: tuple[SignalProcessingStep, ...] = ()

    def to_dict(self) -> dict:
        return {"n_steps": len(self.steps), "steps": [s.to_dict() for s in self.steps]}


@dataclass(frozen=True)
class ArtifactHistory:
    """Ordered record of artifacts detected (and whether each was addressed)."""

    artifacts: tuple[SignalArtifactRecord, ...] = ()
    addressed_artifact_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "n_artifacts": len(self.artifacts),
            "artifacts": [a.to_dict() for a in self.artifacts],
            "addressed_artifact_ids": list(self.addressed_artifact_ids),
        }


@dataclass(frozen=True)
class QualityHistory:
    """Ordered record of quality assessments (before vs after processing)."""

    before: Optional[SignalQualityRecord] = None
    after: Optional[SignalQualityRecord] = None

    def to_dict(self) -> dict:
        return {
            "before": self.before.to_dict() if self.before else None,
            "after": self.after.to_dict() if self.after else None,
            "quality_delta": (
                _q(self.after.recording_quality_score - self.before.recording_quality_score)
                if (self.before and self.after) else None),
        }


# =============================================================================
# Storage projection (processed bytes)
# =============================================================================
@dataclass(frozen=True)
class ProcessedEEGStorageRecord:
    """A reference to the stored *processed* signal bytes + integrity metadata.

    The raw EEG is never touched; the clean signal is written to a separate,
    content-addressed local store (no cloud/S3/db)."""

    storage_id: str
    processed_file_reference: str
    checksum_sha256: str
    content_fingerprint: str
    n_bytes: int
    version: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_refs: tuple[str, ...] = ()
    storage_version: str = SIGNAL_STORAGE_VERSION

    def content_signature(self) -> str:
        return hash_obj({
            "storage_id": self.storage_id, "checksum_sha256": self.checksum_sha256,
            "content_fingerprint": self.content_fingerprint, "n_bytes": self.n_bytes,
        })

    def to_dict(self) -> dict:
        return {
            "storage_id": self.storage_id, "processed_file_reference": self.processed_file_reference,
            "checksum_sha256": self.checksum_sha256, "content_fingerprint": self.content_fingerprint,
            "n_bytes": self.n_bytes, "version": self.version, "created_at": self.created_at,
            "lineage_refs": list(self.lineage_refs), "storage_version": self.storage_version,
            "content_signature": self.content_signature(),
        }


# =============================================================================
# Processed metadata
# =============================================================================
@dataclass(frozen=True)
class ProcessedEEGMetadata:
    """Normalized metadata of the processed signal (deterministic)."""

    n_channels: int
    sampling_frequency: float
    n_samples: int
    duration_seconds: float
    channel_labels: tuple[str, ...]
    applied_filters: tuple[str, ...]
    removal_methods: tuple[str, ...]
    n_artifacts_detected: int
    n_artifacts_addressed: int
    quality_grade: QualityGrade
    metadata_version: str = SIGNAL_DOMAIN_VERSION

    def signature(self) -> str:
        return hash_obj(self.to_dict())

    def to_dict(self) -> dict:
        return {
            "n_channels": self.n_channels, "sampling_frequency": _q(self.sampling_frequency),
            "n_samples": self.n_samples, "duration_seconds": _q(self.duration_seconds),
            "channel_labels": list(self.channel_labels), "applied_filters": list(self.applied_filters),
            "removal_methods": list(self.removal_methods),
            "n_artifacts_detected": self.n_artifacts_detected,
            "n_artifacts_addressed": self.n_artifacts_addressed,
            "quality_grade": self.quality_grade.value, "metadata_version": self.metadata_version,
        }


# =============================================================================
# Audit / lineage / version projections
# =============================================================================
@dataclass(frozen=True)
class SignalAuditRecord:
    """An immutable audit event in the hash-chained signal audit log.

    Field shape matches ``EEGAuditRecord`` / ``CaseAuditRecord`` so the shared
    ``ImmutableAuditLog`` drives it directly (no parallel audit system)."""

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
class SignalLineageRecord:
    """A projection of the shared lineage node attached to a processed asset."""

    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


@dataclass(frozen=True)
class SignalVersion:
    """A content-addressed processed-asset version (chained like EEGVersion)."""

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
class SignalRegistryRecord:
    """The registry entry shape (mutated only via governed registry methods)."""

    processed_id: str
    eeg_asset_id: str
    case_id: str
    patient_id: str
    status: ProcessedAssetStatus
    quality_grade: QualityGrade
    n_artifacts_detected: int
    n_artifacts_addressed: int
    quality_id: str
    processing_id: str
    storage_state: str             # "stored" | "absent"
    version: str
    owner: str
    creation_date: str
    audit_state: str               # audit-log head hash
    lineage_id: str
    dependencies: tuple[str, ...]
    signal_registry_version: str = SIGNAL_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({
            "processed_id": self.processed_id, "eeg_asset_id": self.eeg_asset_id,
            "case_id": self.case_id, "patient_id": self.patient_id, "status": self.status.value,
            "quality_grade": self.quality_grade.value, "version": self.version,
            "lineage_id": self.lineage_id,
        })

    def to_dict(self) -> dict:
        return {
            "processed_id": self.processed_id, "eeg_asset_id": self.eeg_asset_id,
            "case_id": self.case_id, "patient_id": self.patient_id, "status": self.status.value,
            "quality_grade": self.quality_grade.value,
            "n_artifacts_detected": self.n_artifacts_detected,
            "n_artifacts_addressed": self.n_artifacts_addressed, "quality_id": self.quality_id,
            "processing_id": self.processing_id, "storage_state": self.storage_state,
            "version": self.version, "owner": self.owner, "creation_date": self.creation_date,
            "audit_state": self.audit_state, "lineage_id": self.lineage_id,
            "dependencies": list(self.dependencies),
            "signal_registry_version": self.signal_registry_version,
            "content_signature": self.content_signature(),
        }


# =============================================================================
# The aggregate — the processed (clean) EEG asset
# =============================================================================
@dataclass
class ProcessedEEGRecord:
    """The processed-EEG asset aggregate — a permanent, versioned, auditable,
    lineage-tracked record of a *cleaned* signal derived from an immutable raw EEG
    asset. Carries references to the raw + processed signal descriptors, the quality
    assessment, the detected artifacts, the processing record, the histories, the
    processed-signal storage reference, normalized metadata, status, version, owner,
    lineage node, and audit-log head."""

    identity: SignalIdentity
    eeg_asset_id: str
    case_id: str
    patient_id: str
    raw_signal: SignalRecord
    processed_signal: SignalRecord
    quality: SignalQualityRecord
    artifacts: tuple[SignalArtifactRecord, ...]
    processing: SignalProcessingRecord
    processing_history: ProcessingHistory
    artifact_history: ArtifactHistory
    quality_history: QualityHistory
    storage: ProcessedEEGStorageRecord
    metadata: ProcessedEEGMetadata
    status: ProcessedAssetStatus
    version: SignalVersion
    owner: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    dependencies: tuple[str, ...] = ()
    domain_version: str = SIGNAL_DOMAIN_VERSION

    @property
    def processed_id(self) -> str:
        return self.identity.processed_id

    def state_signature(self) -> str:
        return hash_obj({
            "processed_id": self.processed_id, "eeg_asset_id": self.eeg_asset_id,
            "case_id": self.case_id, "patient_id": self.patient_id,
            "raw_signal": self.raw_signal.to_dict(),
            "processed_signal": self.processed_signal.to_dict(),
            "quality_signature": self.quality.signature(),
            "artifacts": [a.signature() for a in self.artifacts],
            "processing_signature": self.processing.signature(),
            "storage_signature": self.storage.content_signature(),
            "metadata_signature": self.metadata.signature(),
            "status": self.status.value, "dependencies": list(self.dependencies),
        })

    def to_dict(self) -> dict:
        return {
            "domain_version": self.domain_version, "identity": self.identity.to_dict(),
            "eeg_asset_id": self.eeg_asset_id, "case_id": self.case_id,
            "patient_id": self.patient_id, "raw_signal": self.raw_signal.to_dict(),
            "processed_signal": self.processed_signal.to_dict(), "quality": self.quality.to_dict(),
            "artifacts": [a.to_dict() for a in self.artifacts], "processing": self.processing.to_dict(),
            "processing_history": self.processing_history.to_dict(),
            "artifact_history": self.artifact_history.to_dict(),
            "quality_history": self.quality_history.to_dict(), "storage": self.storage.to_dict(),
            "metadata": self.metadata.to_dict(), "status": self.status.value,
            "version": self.version.to_dict(), "owner": self.owner, "created_at": self.created_at,
            "lineage_id": self.lineage_id, "audit_head": self.audit_head,
            "dependencies": list(self.dependencies), "state_signature": self.state_signature(),
        }
