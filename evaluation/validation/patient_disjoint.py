"""Patient-disjoint validation — the leakage gate.

Detects patient / session / recording overlap (and hidden leakage) across the
partitions of a split, validates split correctness, and produces the go/no-go
approval. **No evaluation may proceed if leakage exists** (AP-2, NR-3).

The detection works on any :class:`~evaluation.splits.schemas.SplitResult`,
including externally-constructed ones — it verifies disjointness rather than
assuming the generator produced it (defense in depth).
"""

from __future__ import annotations

from evaluation._findings import Finding, Severity
from evaluation.splits.schemas import SplitResult
from evaluation.validation.schemas import (
    ApprovalReport,
    LeakageReport,
    SplitValidationReport,
)


class LeakageError(RuntimeError):
    """Raised when an operation requires a leakage-free split but leakage exists."""

    def __init__(self, report: LeakageReport) -> None:
        super().__init__(
            f"leakage detected in split {report.split_id}: "
            f"{len(report.overlapping_patients)} patient(s), "
            f"{len(report.overlapping_records)} record(s) overlap"
        )
        self.report = report


def detect_leakage(split: SplitResult) -> LeakageReport:
    """Detect cross-partition leakage (patient and record overlap)."""
    patient_to_parts: dict[str, set[str]] = {}
    record_to_parts: dict[str, set[str]] = {}
    for part in split.partitions:
        for pid in part.patient_ids:
            patient_to_parts.setdefault(pid, set()).add(part.name)
        for rid in part.record_ids:
            record_to_parts.setdefault(rid, set()).add(part.name)

    overlapping_patients = tuple(sorted(p for p, parts in patient_to_parts.items() if len(parts) > 1))
    overlapping_records = tuple(sorted(r for r, parts in record_to_parts.items() if len(parts) > 1))

    findings: list[Finding] = []
    if overlapping_patients:
        findings.append(
            Finding(
                "PATIENT_OVERLAP",
                Severity.CRITICAL,
                "one or more patients appear in more than one partition (NR-3 violation)",
                {"patients": list(overlapping_patients), "count": len(overlapping_patients)},
            )
        )
    if overlapping_records:
        findings.append(
            Finding(
                "RECORD_OVERLAP",
                Severity.CRITICAL,
                "one or more recordings/sessions appear in more than one partition",
                {"records": list(overlapping_records), "count": len(overlapping_records)},
            )
        )

    leakage_free = not overlapping_patients and not overlapping_records
    return LeakageReport(
        split_id=split.split_id,
        leakage_free=leakage_free,
        overlapping_patients=overlapping_patients,
        overlapping_records=overlapping_records,
        findings=tuple(findings),
    )


def validate_split(split: SplitResult) -> SplitValidationReport:
    """Validate split correctness and run the leakage gate."""
    leakage = detect_leakage(split)

    findings: list[Finding] = []
    empty = [p.name for p in split.partitions if p.n_patients == 0]
    if empty:
        findings.append(
            Finding(
                "EMPTY_PARTITION",
                Severity.WARNING,
                "one or more partitions have no patients",
                {"partitions": empty},
            )
        )
    if len(split.partitions) < 2:
        findings.append(
            Finding(
                "SINGLE_PARTITION",
                Severity.WARNING,
                "a split should have at least two partitions",
                {"n_partitions": len(split.partitions)},
            )
        )

    partition_summary = {
        p.name: {"n_patients": p.n_patients, "n_records": p.n_records} for p in split.partitions
    }
    valid = leakage.leakage_free and not empty
    return SplitValidationReport(
        split_id=split.split_id,
        scheme=split.spec.scheme,
        valid=valid,
        leakage=leakage,
        findings=tuple(findings),
        partition_summary=partition_summary,
    )


def approve_split(split: SplitResult) -> ApprovalReport:
    """Produce the go/no-go decision for a split (approved iff leakage-free & valid)."""
    report = validate_split(split)
    blocking = tuple(f for f in (*report.leakage.findings, *report.findings)
                     if f.severity is Severity.CRITICAL)
    if report.valid and report.leakage.leakage_free:
        reason = "split is patient-disjoint and structurally valid"
        approved = True
    elif not report.leakage.leakage_free:
        reason = "leakage detected — evaluation must not proceed (NR-3)"
        approved = False
    else:
        reason = "split failed correctness checks"
        approved = False
    return ApprovalReport(
        subject="split",
        subject_id=split.split_id,
        approved=approved,
        reason=reason,
        blocking_findings=blocking,
    )


def require_leakage_free(split: SplitResult) -> LeakageReport:
    """Return the leakage report, raising :class:`LeakageError` if leakage exists."""
    report = detect_leakage(split)
    if not report.leakage_free:
        raise LeakageError(report)
    return report
