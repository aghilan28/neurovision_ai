"""Comprehensive intelligence-report assembly and persistence."""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any

from datasets.schemas.validated_record import ValidatedEegRecord
from evaluation._canonical import canonical_json
from evaluation.dataset_intelligence._provenance import build_provenance
from evaluation.dataset_intelligence.channel_analysis import analyze_channels
from evaluation.dataset_intelligence.distributions import analyze_class_distribution
from evaluation.dataset_intelligence.distributions.labels import DEFAULT_LABEL_MAPPING, LabelMapping
from evaluation.dataset_intelligence.leakage import analyze_leakage_risk
from evaluation.dataset_intelligence.patient_analysis import analyze_patients
from evaluation.dataset_intelligence.profiling import profile_dataset
from evaluation.dataset_intelligence.quality_analysis import analyze_quality
from evaluation.dataset_intelligence.recording_analysis import analyze_recordings
from evaluation.dataset_intelligence.schemas.reports import DatasetIntelligenceReport


def summary_of(
    profile,
    patient,
    channel,
    recording,
    class_distribution,
    quality,
    leakage,
) -> dict[str, Any]:
    """Build the headline summary section of the comprehensive report."""
    return {
        "n_patients": profile.n_patients,
        "n_recordings": profile.n_recordings,
        "n_sessions": profile.n_sessions,
        "total_duration_seconds": profile.duration_stats.stats.total,
        "dataset_size_bytes": profile.dataset_size_bytes,
        "distinct_sampling_rates": recording.distinct_sampling_rates,
        "distinct_channel_configurations": profile.channel_configuration_distribution.n_categories,
        "n_common_channels": len(channel.common_channels),
        "n_classes_present": class_distribution.class_distribution.n_categories,
        "class_imbalance_ratio": class_distribution.imbalance_ratio,
        "labeled_record_fraction": class_distribution.labeled_record_fraction,
        "quality_score": quality.quality_score,
        "leakage_risk_score": leakage.leakage_risk_score,
        "patient_split_ready": patient.split_ready,
    }


def generate_intelligence_report(
    records: Sequence[ValidatedEegRecord],
    *,
    dataset_id: str | None = None,
    dataset_version: str | None = None,
    generated_at: str | None = None,
    label_mapping: LabelMapping = DEFAULT_LABEL_MAPPING,
) -> DatasetIntelligenceReport:
    """Run all analyzers over ``records`` and assemble the comprehensive report.

    A single shared :class:`Provenance` (one input fingerprint, one timestamp) is
    stamped on every sub-report, so the comprehensive report is internally
    consistent and reproducible (AP-6/NR-10).
    """
    prov = build_provenance(
        records, dataset_id=dataset_id, dataset_version=dataset_version, generated_at=generated_at
    )

    profile = profile_dataset(records, provenance=prov)
    patient = analyze_patients(records, provenance=prov)
    channel = analyze_channels(records, provenance=prov)
    recording = analyze_recordings(records, provenance=prov)
    class_distribution = analyze_class_distribution(records, mapping=label_mapping, provenance=prov)
    quality = analyze_quality(records, provenance=prov)
    leakage = analyze_leakage_risk(records, provenance=prov)

    summary = summary_of(profile, patient, channel, recording, class_distribution, quality, leakage)

    return DatasetIntelligenceReport(
        provenance=prov,
        profile=profile,
        patient=patient,
        channel=channel,
        recording=recording,
        class_distribution=class_distribution,
        quality=quality,
        leakage=leakage,
        summary=summary,
    )


def save_report(report: Any, path: str | os.PathLike[str]) -> str:
    """Persist any intelligence report as canonical JSON; returns the path.

    Canonical JSON gives byte-identical output for identical reports, so a stored
    report is itself reproducible and diff-friendly (AP-6/NR-10).
    """
    path = os.fspath(path)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(canonical_json(report.to_dict()))
    return path
