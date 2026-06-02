"""Validation report assembly.

Aggregates individual check findings into a single, deterministic
:class:`~datasets.schemas.reports.ValidationReport` whose overall status is
derived from issue severities.
"""

from __future__ import annotations

from datasets.schemas.reports import ValidationIssue, ValidationReport

#: Validator version, recorded on every report for traceability/reproducibility.
VALIDATOR_VERSION = "1.0.0"


def build_report(
    file_id: str,
    issues: list[ValidationIssue],
    checks_run: tuple[str, ...],
) -> ValidationReport:
    """Build a :class:`ValidationReport` from collected issues.

    Issues are kept in the order produced by the checks (stable/deterministic).
    The status is ``FAILED`` if any ERROR exists, ``PASSED_WITH_WARNINGS`` if any
    WARNING exists, else ``PASSED``.
    """
    issue_tuple = tuple(issues)
    status = ValidationReport.status_for(issue_tuple)
    return ValidationReport(
        file_id=file_id,
        status=status,
        issues=issue_tuple,
        checks_run=checks_run,
        validator_version=VALIDATOR_VERSION,
    )
