"""Dataset-level leakage *risk* analysis (pre-split).

One of the most important parts of the intelligence layer. It does **not** check a
split (that is the Evaluation Foundation's patient-disjoint validator, V1-P4);
instead it surfaces the leakage **risks** inherent in the dataset *before* it is
split, with a risk score, structured findings, recommendations, and an audit trail
(AP-2/NR-3, AP-5/NR-11).

Risks assessed:
- **Duplicate recordings** — identical content (matching SHA-256) that, if placed
  in different partitions, leaks information directly.
- **Patient repetition** — patients with multiple recordings: safe *iff* splitting
  is patient-level; a leakage trap if split per-recording.
- **Missing patient identity** — unknown identities are treated as distinct
  (conservative), but if two records are truly the same patient this could hide
  same-patient leakage.
- **Temporal overlap** — overlapping recordings within a patient.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from datasets.schemas.validated_record import ValidatedEegRecord
from evaluation.dataset_intelligence._provenance import build_provenance
from evaluation.dataset_intelligence.schemas.common import Finding, Provenance, Severity
from evaluation.dataset_intelligence.schemas.reports import LeakageRiskReport

# Risk-score weights (sum <= 1.0). Duplicates are the most direct leakage vector.
_W_DUPLICATE = 0.6
_W_MISSING_IDENTITY = 0.25
_W_TEMPORAL_OVERLAP = 0.15


def _parse_epoch(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso).timestamp()
    except ValueError:
        return None


def _count_temporal_overlap_patients(records: Sequence[ValidatedEegRecord]) -> int:
    by_patient: dict[str, list[tuple[float, float]]] = {}
    for r in records:
        start = _parse_epoch(r.session.start_datetime_iso)
        if start is None:
            continue
        end = start + max(r.metadata.duration_seconds, 0.0)
        by_patient.setdefault(r.patient_id, []).append((start, end))

    overlapping = 0
    for intervals in by_patient.values():
        intervals.sort()
        for (_s1, e1), (s2, _e2) in zip(intervals, intervals[1:], strict=False):
            if s2 < e1:  # next starts before previous ends
                overlapping += 1
                break
    return overlapping


def analyze_leakage_risk(
    records: Sequence[ValidatedEegRecord],
    *,
    provenance: Provenance | None = None,
) -> LeakageRiskReport:
    """Assess pre-split leakage risk for a record set."""
    prov = provenance or build_provenance(records)
    n = len(records)

    findings: list[Finding] = []
    recommendations: list[str] = [
        "Split at the PATIENT level (patient-disjoint); never place two recordings "
        "of the same patient in different partitions (NR-3).",
    ]

    if n == 0:
        return LeakageRiskReport(
            provenance=prov, leakage_risk_score=0.0, findings=(), recommendations=tuple(recommendations),
            audit={"total_records": 0},
        )

    distinct_content = len({r.raw_file.content_sha256 for r in records})
    duplicate_records = n - distinct_content
    duplicate_fraction = duplicate_records / n

    patients = {r.patient_id for r in records}
    by_patient_counts: dict[str, int] = {}
    for r in records:
        by_patient_counts[r.patient_id] = by_patient_counts.get(r.patient_id, 0) + 1
    multi_recording_patients = sum(1 for c in by_patient_counts.values() if c > 1)

    missing_identity = sum(
        1 for r in records if not r.metadata.extra.get("patient_identity_present", False)
    )
    missing_identity_fraction = missing_identity / n

    overlap_patients = _count_temporal_overlap_patients(records)

    if duplicate_records:
        findings.append(Finding(
            "DUPLICATE_RECORDINGS", Severity.CRITICAL,
            "identical recordings (matching content hash) present — a direct cross-split "
            "leakage vector if not deduplicated",
            {"duplicate_records": duplicate_records, "distinct_content": distinct_content}))
        recommendations.append("Deduplicate identical recordings (matching content hash) before splitting.")
    if multi_recording_patients:
        findings.append(Finding(
            "PATIENT_REPETITION", Severity.WARNING,
            "patients have multiple recordings — safe only with patient-level splitting",
            {"patients_with_multiple_recordings": multi_recording_patients,
             "n_patients": len(patients)}))
    if missing_identity:
        findings.append(Finding(
            "MISSING_PATIENT_IDENTITY", Severity.WARNING,
            "records lack a header patient identity; treated as distinct patients "
            "(conservative). If truly the same patient, same-patient leakage could be hidden.",
            {"records_without_identity": missing_identity}))
        recommendations.append(
            "Resolve missing patient identities before splitting where ground truth exists.")
    if overlap_patients:
        findings.append(Finding(
            "TEMPORAL_OVERLAP", Severity.WARNING,
            "overlapping recordings detected within one or more patients",
            {"patients_with_overlap": overlap_patients}))
        recommendations.append("Verify temporal non-overlap within patients before windowing/splitting.")

    recommendations.append(
        "Use the Evaluation Foundation's patient-disjoint validator to enforce zero leakage "
        "before any benchmark is recorded (NR-3).")

    risk_score = min(
        1.0,
        _W_DUPLICATE * duplicate_fraction
        + _W_MISSING_IDENTITY * missing_identity_fraction
        + _W_TEMPORAL_OVERLAP * (1.0 if overlap_patients else 0.0),
    )

    audit = {
        "total_records": n,
        "distinct_content": distinct_content,
        "duplicate_records": duplicate_records,
        "n_patients": len(patients),
        "patients_with_multiple_recordings": multi_recording_patients,
        "records_without_identity": missing_identity,
        "patients_with_temporal_overlap": overlap_patients,
        "weights": {
            "duplicate": _W_DUPLICATE,
            "missing_identity": _W_MISSING_IDENTITY,
            "temporal_overlap": _W_TEMPORAL_OVERLAP,
        },
    }

    return LeakageRiskReport(
        provenance=prov,
        leakage_risk_score=risk_score,
        findings=tuple(findings),
        recommendations=tuple(recommendations),
        audit=audit,
    )
