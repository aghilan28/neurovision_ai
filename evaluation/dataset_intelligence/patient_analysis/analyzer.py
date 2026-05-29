"""Patient intelligence analysis."""

from __future__ import annotations

from collections.abc import Sequence

from datasets.schemas.validated_record import ValidatedEegRecord
from evaluation.dataset_intelligence._provenance import build_provenance
from evaluation.dataset_intelligence.schemas.common import Finding, Provenance, Severity
from evaluation.dataset_intelligence.schemas.reports import PatientAnalysisReport
from evaluation.dataset_intelligence.statistics import numeric_distribution

# Minimum patients to form a 3-way patient-disjoint split (train/val/test).
_MIN_PATIENTS_FOR_SPLIT = 3


def analyze_patients(
    records: Sequence[ValidatedEegRecord],
    *,
    provenance: Provenance | None = None,
) -> PatientAnalysisReport:
    """Analyze patient distribution and patient-disjoint split readiness."""
    prov = provenance or build_provenance(records)

    by_patient: dict[str, list[ValidatedEegRecord]] = {}
    for record in records:
        by_patient.setdefault(record.patient_id, []).append(record)

    n_patients = len(by_patient)
    recordings_per = [len(rs) for rs in by_patient.values()]
    sessions_per = [len({r.session.recording_id for r in rs}) for rs in by_patient.values()]
    duration_per = [sum(r.metadata.duration_seconds for r in rs) for rs in by_patient.values()]

    multi = sum(1 for c in recordings_per if c > 1)
    max_recordings = max(recordings_per) if recordings_per else 0

    missing_identity = sum(
        1 for r in records if not r.metadata.extra.get("patient_identity_present", False)
    )

    findings: list[Finding] = []
    notes: list[str] = []

    split_ready = n_patients >= _MIN_PATIENTS_FOR_SPLIT
    if not split_ready:
        findings.append(
            Finding(
                "INSUFFICIENT_PATIENTS_FOR_SPLIT",
                Severity.WARNING,
                "too few distinct patients to form a patient-disjoint train/val/test split",
                {"n_patients": n_patients, "minimum": _MIN_PATIENTS_FOR_SPLIT},
            )
        )
    else:
        notes.append(
            f"{n_patients} patients available — sufficient for patient-disjoint splitting"
        )

    if multi:
        notes.append(
            f"{multi} patient(s) have multiple recordings — splitting MUST be patient-level (NR-3)"
        )
    if missing_identity:
        findings.append(
            Finding(
                "MISSING_PATIENT_IDENTITY",
                Severity.WARNING,
                "records lack a header patient identity; each is treated as a distinct patient "
                "(conservative for patient-disjoint validation, NR-3)",
                {"records_without_identity": missing_identity},
            )
        )

    return PatientAnalysisReport(
        provenance=prov,
        n_patients=n_patients,
        recordings_per_patient=numeric_distribution("recordings_per_patient", recordings_per),
        sessions_per_patient=numeric_distribution("sessions_per_patient", sessions_per),
        duration_per_patient=numeric_distribution("duration_per_patient_seconds", duration_per),
        patients_with_multiple_recordings=multi,
        max_recordings_for_single_patient=max_recordings,
        split_ready=split_ready,
        findings=tuple(findings),
        notes=tuple(notes),
    )
