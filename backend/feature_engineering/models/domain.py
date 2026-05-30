"""Feature Engineering domain entities + closed vocabularies (Productization P3).

Pure data shapes (JSON-able, content-hashable). No I/O, no orchestration, no
numeric extraction — this module owns only the *shapes* and the *closed
vocabularies* (no free-form states). The engines (frequency / temporal /
connectivity / spectral / topography) produce ``FeatureVector``s; the service groups
them into the immutable ``FeatureRecord`` asset.

Mirrors ``backend.signal_processing.models.domain`` so the feature layer is shaped
exactly like the rest of the platform (NR-6: reuse patterns, don't invent).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    FEATURE_DOMAIN_VERSION, FEATURE_REGISTRY_VERSION,
    FEATURE_VALIDATION_VERSION, DETERMINISTIC_EPOCH, FINGERPRINT_DECIMALS,
)


def _q(x: float) -> float:
    return round(float(x), FINGERPRINT_DECIMALS)


def _qlist(values) -> list:
    return [round(float(v), FINGERPRINT_DECIMALS) for v in values]


# =============================================================================
# Closed vocabularies (no free-form states)
# =============================================================================
class FeatureFamily(str, Enum):
    """The five feature families produced by the engines."""

    FREQUENCY = "frequency"
    TEMPORAL = "temporal"
    CONNECTIVITY = "connectivity"
    SPECTRAL = "spectral"
    TOPOGRAPHY = "topography"


class FeatureGroup(str, Enum):
    """The closed set of feature groups within the families."""

    # frequency
    BAND_POWER = "band_power"
    BAND_RATIO = "band_ratio"
    RELATIVE_POWER = "relative_power"
    SPECTRAL_ENTROPY = "spectral_entropy"
    # temporal
    STATISTICAL = "statistical"
    HJORTH = "hjorth"
    SIGNAL_ENTROPY = "signal_entropy"
    # connectivity
    COHERENCE = "coherence"
    PHASE_LOCKING = "phase_locking"
    CROSS_CORRELATION = "cross_correlation"
    SYNCHRONIZATION = "synchronization"
    # spectral representations
    PSD = "psd"
    SPECTROGRAM = "spectrogram"
    BAND_SUMMARY = "band_summary"
    FREQUENCY_HISTOGRAM = "frequency_histogram"
    # topography
    CHANNEL_LAYOUT = "channel_layout"
    REGIONAL = "regional"
    SPATIAL_SUMMARY = "spatial_summary"
    TOPOGRAPHIC_STAT = "topographic_stat"


class FeatureScope(str, Enum):
    """How a feature vector is indexed (its dimensional meaning)."""

    PER_CHANNEL = "per_channel"
    PER_RECORDING = "per_recording"
    PER_CHANNEL_PAIR = "per_channel_pair"
    PER_REGION = "per_region"
    PER_BAND = "per_band"
    PER_BAND_CHANNEL = "per_band_channel"


class FrequencyBand(str, Enum):
    """Canonical EEG frequency bands (Hz ranges via ``hz``)."""

    DELTA = "delta"
    THETA = "theta"
    ALPHA = "alpha"
    BETA = "beta"
    GAMMA = "gamma"

    @property
    def hz(self) -> tuple[float, float]:
        return {
            "delta": (0.5, 4.0), "theta": (4.0, 8.0), "alpha": (8.0, 13.0),
            "beta": (13.0, 30.0), "gamma": (30.0, 45.0),
        }[self.value]


class FeatureAssetStatus(str, Enum):
    """The standing of a feature asset (deliberately tiny; no workflow)."""

    GENERATED = "generated"
    QUARANTINED = "quarantined"


class FeatureValidationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# =============================================================================
# Identity projection
# =============================================================================
@dataclass(frozen=True)
class FeatureIdentity:
    """A feature-asset identity, derived (content-addressed) from a processed asset
    id + the feature-extraction fingerprint. Never filename-derived."""

    feature_asset_id: str
    processed_id: str
    identity_version: str
    domain_version: str = FEATURE_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {
            "feature_asset_id": self.feature_asset_id, "processed_id": self.processed_id,
            "identity_version": self.identity_version, "domain_version": self.domain_version,
        }


# =============================================================================
# Feature vector (atomic numeric output)
# =============================================================================
@dataclass(frozen=True)
class FeatureVector:
    """An atomic numeric feature output: named values with dimensional labels.

    Scalars use a 1-element ``values``; per-channel features use one value per
    channel; matrices (e.g. a connectivity or spectrogram tensor) are stored as a
    flattened ``values`` tuple with ``shape`` + ``axes`` so they remain structured
    and deterministic. ``content_fingerprint`` is content-addressed.
    """

    name: str
    family: FeatureFamily
    group: FeatureGroup
    scope: FeatureScope
    labels: tuple[str, ...]
    values: tuple[float, ...]
    shape: tuple[int, ...]
    axes: tuple[str, ...] = ()
    units: str = ""

    @property
    def content_fingerprint(self) -> str:
        return hash_obj({
            "name": self.name, "family": self.family.value, "group": self.group.value,
            "scope": self.scope.value, "labels": list(self.labels), "shape": list(self.shape),
            "axes": list(self.axes), "values": _qlist(self.values),
        })

    @property
    def n_values(self) -> int:
        return len(self.values)

    def to_dict(self) -> dict:
        return {
            "name": self.name, "family": self.family.value, "group": self.group.value,
            "scope": self.scope.value, "labels": list(self.labels), "shape": list(self.shape),
            "axes": list(self.axes), "units": self.units, "n_values": self.n_values,
            "values": _qlist(self.values), "content_fingerprint": self.content_fingerprint,
        }


# =============================================================================
# Feature group (organizes vectors by family)
# =============================================================================
@dataclass(frozen=True)
class FeatureGroupRecord:
    """A collection of feature vectors sharing a family (organizational unit)."""

    family: FeatureFamily
    vectors: tuple[FeatureVector, ...] = ()

    @property
    def n_vectors(self) -> int:
        return len(self.vectors)

    @property
    def groups(self) -> tuple[str, ...]:
        return tuple(sorted({v.group.value for v in self.vectors}))

    def signature(self) -> str:
        return hash_obj({"family": self.family.value,
                         "vectors": [v.content_fingerprint for v in self.vectors]})

    def to_dict(self) -> dict:
        return {
            "family": self.family.value, "n_vectors": self.n_vectors, "groups": list(self.groups),
            "vectors": [v.to_dict() for v in self.vectors], "group_signature": self.signature(),
        }


# =============================================================================
# Metadata
# =============================================================================
@dataclass(frozen=True)
class FeatureMetadata:
    """Normalized, deterministic metadata for a feature asset."""

    processed_id: str
    eeg_asset_id: str
    n_channels: int
    sampling_frequency: float
    n_samples: int
    duration_seconds: float
    channel_labels: tuple[str, ...]
    families_present: tuple[str, ...]
    groups_present: tuple[str, ...]
    n_vectors: int
    n_values_total: int
    frequency_bands: dict
    extraction_config: dict
    metadata_version: str = FEATURE_DOMAIN_VERSION

    def signature(self) -> str:
        return hash_obj(self._core())

    def _core(self) -> dict:
        return {
            "processed_id": self.processed_id, "eeg_asset_id": self.eeg_asset_id,
            "n_channels": self.n_channels, "sampling_frequency": _q(self.sampling_frequency),
            "n_samples": self.n_samples, "duration_seconds": _q(self.duration_seconds),
            "channel_labels": list(self.channel_labels),
            "families_present": list(self.families_present),
            "groups_present": list(self.groups_present), "n_vectors": self.n_vectors,
            "n_values_total": self.n_values_total,
            "frequency_bands": {k: list(v) for k, v in sorted(self.frequency_bands.items())},
            "extraction_config": dict(sorted(self.extraction_config.items())),
        }

    def to_dict(self) -> dict:
        return {**self._core(), "metadata_version": self.metadata_version,
                "metadata_signature": self.signature()}


# =============================================================================
# Validation projection
# =============================================================================
@dataclass(frozen=True)
class FeatureValidationRecord:
    """A persisted projection of the feature-asset integrity validation."""

    validation_id: str
    ok: bool
    checks: tuple[tuple, ...]            # (name, passed, detail)
    validation_version: str = FEATURE_VALIDATION_VERSION

    @property
    def n_checks(self) -> int:
        return len(self.checks)

    @property
    def n_passed(self) -> int:
        return sum(1 for _, passed, _ in self.checks if passed)

    def signature(self) -> str:
        return hash_obj({"ok": self.ok,
                         "checks": [[n, bool(p)] for n, p, _ in self.checks]})

    def to_dict(self) -> dict:
        return {
            "validation_id": self.validation_id, "ok": self.ok, "n_checks": self.n_checks,
            "n_passed": self.n_passed,
            "checks": [{"name": n, "passed": bool(p), "detail": d} for n, p, d in self.checks],
            "validation_version": self.validation_version, "validation_signature": self.signature(),
        }


# =============================================================================
# Audit / lineage / version projections
# =============================================================================
@dataclass(frozen=True)
class FeatureAuditRecord:
    """An immutable audit event in the hash-chained feature audit log.

    Field shape matches ``SignalAuditRecord`` / ``EEGAuditRecord`` so the shared
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
            "prev_hash": self.prev_hash, "event_hash": self.event_hash, "created_at": self.created_at,
        }


@dataclass(frozen=True)
class FeatureLineageRecord:
    """A projection of the shared lineage node attached to a feature asset."""

    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


@dataclass(frozen=True)
class FeatureVersion:
    """A content-addressed feature-asset version (chained like SignalVersion)."""

    version: str
    previous: Optional[str]
    reason: str
    created_at: str = DETERMINISTIC_EPOCH

    @staticmethod
    def compute(state_signature: str, previous: Optional[str]) -> str:
        return hash_obj({"state": state_signature, "previous": previous})

    def to_dict(self) -> dict:
        return {"version": self.version, "previous": self.previous,
                "reason": self.reason, "created_at": self.created_at}


# =============================================================================
# Registry record
# =============================================================================
@dataclass
class FeatureRegistryRecord:
    """The registry entry shape (mutated only via governed registry methods)."""

    feature_asset_id: str
    processed_id: str
    eeg_asset_id: str
    case_id: str
    patient_id: str
    status: FeatureAssetStatus
    families: tuple[str, ...]
    groups: tuple[str, ...]
    n_vectors: int
    n_values_total: int
    version: str
    owner: str
    creation_date: str
    audit_state: str
    lineage_id: str
    dependencies: tuple[str, ...]
    feature_registry_version: str = FEATURE_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({
            "feature_asset_id": self.feature_asset_id, "processed_id": self.processed_id,
            "eeg_asset_id": self.eeg_asset_id, "case_id": self.case_id, "patient_id": self.patient_id,
            "status": self.status.value, "families": list(self.families), "version": self.version,
            "lineage_id": self.lineage_id,
        })

    def to_dict(self) -> dict:
        return {
            "feature_asset_id": self.feature_asset_id, "processed_id": self.processed_id,
            "eeg_asset_id": self.eeg_asset_id, "case_id": self.case_id, "patient_id": self.patient_id,
            "status": self.status.value, "families": list(self.families), "groups": list(self.groups),
            "n_vectors": self.n_vectors, "n_values_total": self.n_values_total, "version": self.version,
            "owner": self.owner, "creation_date": self.creation_date, "audit_state": self.audit_state,
            "lineage_id": self.lineage_id, "dependencies": list(self.dependencies),
            "feature_registry_version": self.feature_registry_version,
            "content_signature": self.content_signature(),
        }


# =============================================================================
# The aggregate — the immutable Feature Asset
# =============================================================================
@dataclass(frozen=True)
class FeatureRecord:
    """The feature-asset aggregate — an **immutable**, versioned, auditable,
    lineage-tracked record of the validated features derived from a processed EEG
    asset. Holds the feature groups (organized by family), the flat list of feature
    vectors, normalized metadata, the validation record, status, version, owner,
    lineage node, and audit-log head. It carries no raw signal."""

    identity: FeatureIdentity
    processed_id: str
    eeg_asset_id: str
    case_id: str
    patient_id: str
    groups: tuple[FeatureGroupRecord, ...]
    metadata: FeatureMetadata
    validation: FeatureValidationRecord
    status: FeatureAssetStatus
    version: FeatureVersion
    owner: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    dependencies: tuple[str, ...] = ()
    domain_version: str = FEATURE_DOMAIN_VERSION

    @property
    def feature_asset_id(self) -> str:
        return self.identity.feature_asset_id

    @property
    def vectors(self) -> tuple[FeatureVector, ...]:
        return tuple(v for g in self.groups for v in g.vectors)

    @property
    def families(self) -> tuple[str, ...]:
        return tuple(sorted({g.family.value for g in self.groups}))

    @property
    def group_names(self) -> tuple[str, ...]:
        return tuple(sorted({v.group.value for v in self.vectors}))

    @staticmethod
    def state_signature_of(*, identity, processed_id, eeg_asset_id, case_id, patient_id,
                           groups, metadata, validation, status, dependencies) -> str:
        """Content hash of the immutable asset state (basis of FeatureVersion).

        Excludes version + audit_head so the version can chain over it."""
        return hash_obj({
            "feature_asset_id": identity.feature_asset_id, "processed_id": processed_id,
            "eeg_asset_id": eeg_asset_id, "case_id": case_id, "patient_id": patient_id,
            "groups": [g.signature() for g in groups], "metadata_signature": metadata.signature(),
            "validation_signature": validation.signature(), "status": status.value,
            "dependencies": list(dependencies),
        })

    def state_signature(self) -> str:
        return self.state_signature_of(
            identity=self.identity, processed_id=self.processed_id, eeg_asset_id=self.eeg_asset_id,
            case_id=self.case_id, patient_id=self.patient_id, groups=self.groups,
            metadata=self.metadata, validation=self.validation, status=self.status,
            dependencies=self.dependencies)

    def to_dict(self) -> dict:
        return {
            "domain_version": self.domain_version, "identity": self.identity.to_dict(),
            "processed_id": self.processed_id, "eeg_asset_id": self.eeg_asset_id,
            "case_id": self.case_id, "patient_id": self.patient_id,
            "families": list(self.families), "group_names": list(self.group_names),
            "n_vectors": len(self.vectors),
            "groups": [g.to_dict() for g in self.groups], "metadata": self.metadata.to_dict(),
            "validation": self.validation.to_dict(), "status": self.status.value,
            "version": self.version.to_dict(), "owner": self.owner, "created_at": self.created_at,
            "lineage_id": self.lineage_id, "audit_head": self.audit_head,
            "dependencies": list(self.dependencies), "state_signature": self.state_signature(),
        }
