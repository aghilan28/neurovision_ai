"""Report contracts for the Dataset Intelligence Layer.

Each report is a frozen, serializable artifact stamped with :class:`Provenance` and
exposing a ``content_fingerprint`` that **excludes** volatile timestamps, so two
reports over the same data + same versions fingerprint identically (reproducible,
AP-6/NR-10).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from evaluation._canonical import canonical_fingerprint
from evaluation.dataset_intelligence.schemas.common import (
    CategoryDistribution,
    Finding,
    NumericDistribution,
    Provenance,
)


def _strip_volatile(value: Any) -> Any:
    """Recursively remove volatile ``generated_at`` keys for fingerprinting."""
    if isinstance(value, dict):
        return {k: _strip_volatile(v) for k, v in value.items() if k != "generated_at"}
    if isinstance(value, list):
        return [_strip_volatile(v) for v in value]
    return value


def _fingerprint(payload: dict[str, Any]) -> str:
    return canonical_fingerprint(_strip_volatile(payload))


@dataclass(frozen=True, slots=True)
class DatasetProfile:
    """High-level reproducible profile of a dataset (counts, durations, configs)."""

    provenance: Provenance
    dataset_size_bytes: int
    n_patients: int
    n_recordings: int
    n_sessions: int
    duration_stats: NumericDistribution
    sampling_frequency_distribution: CategoryDistribution
    channel_configuration_distribution: CategoryDistribution
    annotation_coverage: dict[str, Any]
    dataset_versions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance": self.provenance.to_dict(),
            "dataset_size_bytes": self.dataset_size_bytes,
            "n_patients": self.n_patients,
            "n_recordings": self.n_recordings,
            "n_sessions": self.n_sessions,
            "duration_stats": self.duration_stats.to_dict(),
            "sampling_frequency_distribution": self.sampling_frequency_distribution.to_dict(),
            "channel_configuration_distribution": self.channel_configuration_distribution.to_dict(),
            "annotation_coverage": self.annotation_coverage,
            "dataset_versions": list(self.dataset_versions),
        }

    @property
    def content_fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


@dataclass(frozen=True, slots=True)
class PatientAnalysisReport:
    """Patient intelligence: distribution, repetition, and split readiness."""

    provenance: Provenance
    n_patients: int
    recordings_per_patient: NumericDistribution
    sessions_per_patient: NumericDistribution
    duration_per_patient: NumericDistribution
    patients_with_multiple_recordings: int
    max_recordings_for_single_patient: int
    split_ready: bool
    findings: tuple[Finding, ...] = ()
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance": self.provenance.to_dict(),
            "n_patients": self.n_patients,
            "recordings_per_patient": self.recordings_per_patient.to_dict(),
            "sessions_per_patient": self.sessions_per_patient.to_dict(),
            "duration_per_patient": self.duration_per_patient.to_dict(),
            "patients_with_multiple_recordings": self.patients_with_multiple_recordings,
            "max_recordings_for_single_patient": self.max_recordings_for_single_patient,
            "split_ready": self.split_ready,
            "findings": [f.to_dict() for f in self.findings],
            "notes": list(self.notes),
        }

    @property
    def content_fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


@dataclass(frozen=True, slots=True)
class ChannelInventoryEntry:
    """One channel's presence across the dataset."""

    label: str
    channel_type: str
    occurrence_count: int
    availability_fraction: float
    sampling_frequencies_hz: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "channel_type": self.channel_type,
            "occurrence_count": self.occurrence_count,
            "availability_fraction": self.availability_fraction,
            "sampling_frequencies_hz": list(self.sampling_frequencies_hz),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChannelInventoryEntry:
        return cls(
            label=data["label"],
            channel_type=data["channel_type"],
            occurrence_count=int(data["occurrence_count"]),
            availability_fraction=float(data["availability_fraction"]),
            sampling_frequencies_hz=tuple(float(x) for x in data.get("sampling_frequencies_hz", ())),
        )


@dataclass(frozen=True, slots=True)
class ChannelAnalysisReport:
    """Channel inventory + montage/cross-dataset compatibility."""

    provenance: Provenance
    inventory: tuple[ChannelInventoryEntry, ...]
    common_channels: tuple[str, ...]
    montage_compatibility: dict[str, Any]
    compatibility_matrix: dict[str, Any]
    findings: tuple[Finding, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance": self.provenance.to_dict(),
            "inventory": [e.to_dict() for e in self.inventory],
            "common_channels": list(self.common_channels),
            "montage_compatibility": self.montage_compatibility,
            "compatibility_matrix": self.compatibility_matrix,
            "findings": [f.to_dict() for f in self.findings],
        }

    @property
    def content_fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


@dataclass(frozen=True, slots=True)
class RecordingAnalysisReport:
    """Recording intelligence: lengths, sampling, annotations, variability."""

    provenance: Provenance
    length_seconds: NumericDistribution
    sampling_frequency_distribution: CategoryDistribution
    annotations_per_recording: NumericDistribution
    distinct_durations: int
    distinct_sampling_rates: int
    temporal_distribution: CategoryDistribution
    findings: tuple[Finding, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance": self.provenance.to_dict(),
            "length_seconds": self.length_seconds.to_dict(),
            "sampling_frequency_distribution": self.sampling_frequency_distribution.to_dict(),
            "annotations_per_recording": self.annotations_per_recording.to_dict(),
            "distinct_durations": self.distinct_durations,
            "distinct_sampling_rates": self.distinct_sampling_rates,
            "temporal_distribution": self.temporal_distribution.to_dict(),
            "findings": [f.to_dict() for f in self.findings],
        }

    @property
    def content_fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


@dataclass(frozen=True, slots=True)
class ClassDistributionReport:
    """Class/label distribution analysis (analysis only — no balancing)."""

    provenance: Provenance
    class_distribution: CategoryDistribution
    family_distribution: CategoryDistribution
    rare_classes: tuple[str, ...]
    imbalance_ratio: float
    labeled_record_fraction: float
    findings: tuple[Finding, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance": self.provenance.to_dict(),
            "class_distribution": self.class_distribution.to_dict(),
            "family_distribution": self.family_distribution.to_dict(),
            "rare_classes": list(self.rare_classes),
            "imbalance_ratio": self.imbalance_ratio,
            "labeled_record_fraction": self.labeled_record_fraction,
            "findings": [f.to_dict() for f in self.findings],
        }

    @property
    def content_fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


@dataclass(frozen=True, slots=True)
class QualityAnalysisReport:
    """Dataset-level data-quality scoring (report-only)."""

    provenance: Provenance
    quality_score: float  # 0.0 (worst) .. 1.0 (best)
    component_scores: dict[str, float]
    counts: dict[str, int]
    findings: tuple[Finding, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance": self.provenance.to_dict(),
            "quality_score": self.quality_score,
            "component_scores": self.component_scores,
            "counts": self.counts,
            "findings": [f.to_dict() for f in self.findings],
        }

    @property
    def content_fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


@dataclass(frozen=True, slots=True)
class LeakageRiskReport:
    """Dataset-level leakage *risk* assessment (pre-split)."""

    provenance: Provenance
    leakage_risk_score: float  # 0.0 (no risk) .. 1.0 (severe risk)
    findings: tuple[Finding, ...]
    recommendations: tuple[str, ...]
    audit: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance": self.provenance.to_dict(),
            "leakage_risk_score": self.leakage_risk_score,
            "findings": [f.to_dict() for f in self.findings],
            "recommendations": list(self.recommendations),
            "audit": self.audit,
        }

    @property
    def content_fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


@dataclass(frozen=True, slots=True)
class DatasetIntelligenceReport:
    """The comprehensive intelligence report aggregating all sub-reports."""

    provenance: Provenance
    profile: DatasetProfile
    patient: PatientAnalysisReport
    channel: ChannelAnalysisReport
    recording: RecordingAnalysisReport
    class_distribution: ClassDistributionReport
    quality: QualityAnalysisReport
    leakage: LeakageRiskReport
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance": self.provenance.to_dict(),
            "summary": self.summary,
            "profile": self.profile.to_dict(),
            "patient": self.patient.to_dict(),
            "channel": self.channel.to_dict(),
            "recording": self.recording.to_dict(),
            "class_distribution": self.class_distribution.to_dict(),
            "quality": self.quality.to_dict(),
            "leakage": self.leakage.to_dict(),
            "sub_report_fingerprints": {
                "profile": self.profile.content_fingerprint,
                "patient": self.patient.content_fingerprint,
                "channel": self.channel.content_fingerprint,
                "recording": self.recording.content_fingerprint,
                "class_distribution": self.class_distribution.content_fingerprint,
                "quality": self.quality.content_fingerprint,
                "leakage": self.leakage.content_fingerprint,
            },
        }

    @property
    def content_fingerprint(self) -> str:
        return _fingerprint(self.to_dict())
