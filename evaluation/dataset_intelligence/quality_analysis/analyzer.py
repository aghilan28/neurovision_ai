"""Dataset-level data-quality scoring."""

from __future__ import annotations

from collections.abc import Sequence

from datasets.schemas.validated_record import ValidatedEegRecord
from evaluation.dataset_intelligence._provenance import build_provenance
from evaluation.dataset_intelligence.schemas.common import Finding, Provenance, Severity
from evaluation.dataset_intelligence.schemas.reports import QualityAnalysisReport


def _annotation_problem(record: ValidatedEegRecord) -> bool:
    duration = record.metadata.duration_seconds
    for ann in record.metadata.annotations:
        if ann.onset_seconds < 0:
            return True
        if duration > 0 and ann.onset_seconds > duration + 1e-6:
            return True
        if ann.duration_seconds is not None and ann.duration_seconds < 0:
            return True
    return False


def analyze_quality(
    records: Sequence[ValidatedEegRecord],
    *,
    provenance: Provenance | None = None,
) -> QualityAnalysisReport:
    """Compute a deterministic dataset quality score (0..1) with findings."""
    prov = provenance or build_provenance(records)
    n = len(records)

    if n == 0:
        return QualityAnalysisReport(
            provenance=prov, quality_score=0.0, component_scores={}, counts={},
            findings=(Finding("EMPTY_DATASET", Severity.WARNING, "no records to assess"),),
        )

    corrupted = sum(1 for r in records if not r.validation.status.is_acceptable)
    missing_metadata = sum(
        1
        for r in records
        if r.metadata.recording_date_iso is None
        or not r.metadata.extra.get("patient_identity_present", False)
    )
    missing_channels = sum(1 for r in records if r.metadata.data_channel_count == 0)
    inconsistent_sampling = sum(1 for r in records if not r.metadata.is_uniform_sampling)
    annotation_problems = sum(1 for r in records if _annotation_problem(r))

    distinct_content = len({r.raw_file.content_sha256 for r in records})
    duplicate_recordings = n - distinct_content

    counts = {
        "corrupted_records": corrupted,
        "records_missing_metadata": missing_metadata,
        "records_missing_channels": missing_channels,
        "inconsistent_sampling_records": inconsistent_sampling,
        "annotation_problem_records": annotation_problems,
        "duplicate_recordings": duplicate_recordings,
        "total_records": n,
    }

    # Component scores (1.0 == perfect), equally weighted.
    component_scores = {
        "validation": 1.0 - corrupted / n,
        "metadata_completeness": 1.0 - missing_metadata / n,
        "channel_completeness": 1.0 - missing_channels / n,
        "sampling_consistency": 1.0 - inconsistent_sampling / n,
        "annotation_sanity": 1.0 - annotation_problems / n,
        "uniqueness": 1.0 - duplicate_recordings / n,
    }
    quality_score = sum(component_scores.values()) / len(component_scores)

    findings: list[Finding] = []
    if corrupted:
        findings.append(Finding(
            "CORRUPTED_OR_QUARANTINED_RECORDS", Severity.CRITICAL,
            "records failed validation (corrupted/quarantined)", {"count": corrupted}))
    if duplicate_recordings:
        findings.append(Finding(
            "DUPLICATE_RECORDINGS", Severity.WARNING,
            "identical recordings detected by content hash (deduplicate before splitting)",
            {"count": duplicate_recordings}))
    if missing_channels:
        findings.append(Finding(
            "RECORDS_WITHOUT_DATA_CHANNELS", Severity.WARNING,
            "records have no data channels", {"count": missing_channels}))
    if inconsistent_sampling:
        findings.append(Finding(
            "INCONSISTENT_SAMPLING", Severity.WARNING,
            "records mix sampling rates across data channels", {"count": inconsistent_sampling}))
    if annotation_problems:
        findings.append(Finding(
            "ANNOTATION_PROBLEMS", Severity.WARNING,
            "records contain annotations with invalid onset/duration", {"count": annotation_problems}))
    if missing_metadata:
        findings.append(Finding(
            "INCOMPLETE_METADATA", Severity.INFO,
            "records missing recording date and/or patient identity", {"count": missing_metadata}))

    return QualityAnalysisReport(
        provenance=prov,
        quality_score=quality_score,
        component_scores=component_scores,
        counts=counts,
        findings=tuple(findings),
    )
