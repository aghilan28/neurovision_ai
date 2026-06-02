"""Schemas for evaluation validation reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from evaluation._findings import Finding

#: Version of the evaluation-validation logic (recorded on reports).
VALIDATION_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class LeakageReport:
    """Result of leakage detection over a split (the cardinal check)."""

    split_id: str
    leakage_free: bool
    overlapping_patients: tuple[str, ...] = ()
    overlapping_records: tuple[str, ...] = ()
    findings: tuple[Finding, ...] = ()
    validation_version: str = VALIDATION_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "split_id": self.split_id,
            "leakage_free": self.leakage_free,
            "overlapping_patients": list(self.overlapping_patients),
            "overlapping_records": list(self.overlapping_records),
            "findings": [f.to_dict() for f in self.findings],
            "validation_version": self.validation_version,
        }


@dataclass(frozen=True, slots=True)
class SplitValidationReport:
    """Split correctness + embedded leakage result."""

    split_id: str
    scheme: str
    valid: bool
    leakage: LeakageReport
    findings: tuple[Finding, ...] = ()
    partition_summary: dict[str, Any] = field(default_factory=dict)
    validation_version: str = VALIDATION_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "split_id": self.split_id,
            "scheme": self.scheme,
            "valid": self.valid,
            "leakage": self.leakage.to_dict(),
            "findings": [f.to_dict() for f in self.findings],
            "partition_summary": self.partition_summary,
            "validation_version": self.validation_version,
        }


@dataclass(frozen=True, slots=True)
class ApprovalReport:
    """The go/no-go decision for a split or evaluation run."""

    subject: str  # "split" | "evaluation"
    subject_id: str
    approved: bool
    reason: str
    blocking_findings: tuple[Finding, ...] = ()
    validation_version: str = VALIDATION_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "subject_id": self.subject_id,
            "approved": self.approved,
            "reason": self.reason,
            "blocking_findings": [f.to_dict() for f in self.blocking_findings],
            "validation_version": self.validation_version,
        }
