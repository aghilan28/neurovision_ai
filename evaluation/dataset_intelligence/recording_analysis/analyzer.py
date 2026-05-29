"""Recording intelligence analysis."""

from __future__ import annotations

from collections.abc import Sequence

from datasets.schemas.validated_record import ValidatedEegRecord
from evaluation.dataset_intelligence._provenance import build_provenance
from evaluation.dataset_intelligence.distributions.dataset_distributions import (
    annotation_count_distribution,
    duration_distribution,
    sampling_frequency_distribution,
)
from evaluation.dataset_intelligence.schemas.common import Finding, Provenance, Severity
from evaluation.dataset_intelligence.schemas.reports import RecordingAnalysisReport
from evaluation.dataset_intelligence.statistics import category_counts


def _temporal_key(record: ValidatedEegRecord) -> str:
    """Year-month bucket from the recording date (``"unknown"`` if absent)."""
    iso = record.metadata.recording_date_iso
    if iso and len(iso) >= 7:
        return iso[:7]  # YYYY-MM
    return "unknown"


def analyze_recordings(
    records: Sequence[ValidatedEegRecord],
    *,
    provenance: Provenance | None = None,
) -> RecordingAnalysisReport:
    """Analyze recording lengths, sampling, annotations, variability, and timing."""
    prov = provenance or build_provenance(records)

    distinct_durations = len({round(r.metadata.duration_seconds, 3) for r in records})
    sampling_keys = set()
    for r in records:
        freqs = r.metadata.sampling_frequencies_hz
        sampling_keys.add(freqs[0] if freqs else None)
    distinct_sampling = len(sampling_keys)

    temporal = category_counts("recording_month", [_temporal_key(r) for r in records])

    findings: list[Finding] = []
    if distinct_sampling > 1:
        findings.append(
            Finding(
                "MIXED_SAMPLING_RATES",
                Severity.WARNING,
                "recordings use more than one sampling rate; resampling to a common rate is "
                "required before cross-recording analysis (preprocessing owns this)",
                {"distinct_sampling_rates": distinct_sampling},
            )
        )
    missing_dates = sum(1 for r in records if not r.metadata.recording_date_iso)
    if missing_dates:
        findings.append(
            Finding(
                "MISSING_RECORDING_DATES",
                Severity.INFO,
                "some recordings have no parseable recording date",
                {"records_without_date": missing_dates},
            )
        )

    return RecordingAnalysisReport(
        provenance=prov,
        length_seconds=duration_distribution(records),
        sampling_frequency_distribution=sampling_frequency_distribution(records),
        annotations_per_recording=annotation_count_distribution(records),
        distinct_durations=distinct_durations,
        distinct_sampling_rates=distinct_sampling,
        temporal_distribution=temporal,
        findings=tuple(findings),
    )
