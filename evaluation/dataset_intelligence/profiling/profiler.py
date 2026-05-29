"""Dataset profiling."""

from __future__ import annotations

from collections.abc import Sequence

from datasets.schemas.validated_record import ValidatedEegRecord
from evaluation.dataset_intelligence._provenance import build_provenance
from evaluation.dataset_intelligence.distributions.dataset_distributions import (
    channel_configuration_distribution,
    duration_distribution,
    sampling_frequency_distribution,
)
from evaluation.dataset_intelligence.schemas.common import Provenance
from evaluation.dataset_intelligence.schemas.reports import DatasetProfile


def profile_dataset(
    records: Sequence[ValidatedEegRecord],
    *,
    dataset_id: str | None = None,
    dataset_version: str | None = None,
    generated_at: str | None = None,
    provenance: Provenance | None = None,
) -> DatasetProfile:
    """Build a reproducible :class:`DatasetProfile` for a record set."""
    prov = provenance or build_provenance(
        records, dataset_id=dataset_id, dataset_version=dataset_version, generated_at=generated_at
    )

    patients = {r.patient_id for r in records}
    sessions = {r.session.recording_id for r in records}
    total_annotations = sum(len(r.metadata.annotations) for r in records)
    records_with_annotations = sum(1 for r in records if r.metadata.annotations)
    n = len(records)

    annotation_coverage = {
        "records_with_annotations": records_with_annotations,
        "total_annotations": total_annotations,
        "fraction_with_annotations": (records_with_annotations / n) if n else 0.0,
        "mean_annotations_per_record": (total_annotations / n) if n else 0.0,
    }

    return DatasetProfile(
        provenance=prov,
        dataset_size_bytes=sum(r.raw_file.file_size_bytes for r in records),
        n_patients=len(patients),
        n_recordings=n,
        n_sessions=len(sessions),
        duration_stats=duration_distribution(records),
        sampling_frequency_distribution=sampling_frequency_distribution(records),
        channel_configuration_distribution=channel_configuration_distribution(records),
        annotation_coverage=annotation_coverage,
        dataset_versions=tuple(v for v in (dataset_version,) if v),
    )
