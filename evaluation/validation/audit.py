"""Evaluation audit: split correctness, leakage, metric/version/lineage consistency.

Produces a deterministic audit verdict over the components of an evaluation run, so
a completed run can be re-checked for scientific validity (AP-6/AP-8, NR-10/NR-11).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from evaluation._findings import Finding, Severity
from evaluation._provenance import VersionBundle
from evaluation._version import EVALUATION_VERSION
from evaluation.lineage.tracker import EvaluationLineage
from evaluation.metrics.registry import METRICS_VERSION
from evaluation.metrics.schemas import MetricKind, MetricResult
from evaluation.validation.schemas import ApprovalReport, SplitValidationReport

#: Metric kinds whose scalar value must lie in [0, 1].
_BOUNDED_KINDS = {MetricKind.CLASSIFICATION, MetricKind.RANKING}


def audit_evaluation(
    *,
    versions: VersionBundle,
    split_id: str,
    split_validation: SplitValidationReport,
    approval: ApprovalReport,
    metric_results: Mapping[str, MetricResult],
    lineage: EvaluationLineage | None,
    benchmark_present: bool,
) -> dict[str, Any]:
    """Audit a run's components and return ``{ok, findings, checks}``."""
    findings: list[Finding] = []

    # 1) Split correctness.
    if not split_validation.valid:
        findings.append(Finding("SPLIT_INVALID", Severity.CRITICAL,
                                 "split failed correctness validation"))

    # 2) Leakage absence (the cardinal check).
    if not split_validation.leakage.leakage_free:
        findings.append(Finding("LEAKAGE_PRESENT", Severity.CRITICAL,
                                 "leakage detected — results are not scientifically valid (NR-3)"))

    # 3) Metric validity.
    for name, result in metric_results.items():
        if result.value is not None:
            if not math.isfinite(result.value):
                findings.append(Finding("METRIC_NOT_FINITE", Severity.CRITICAL,
                                         "metric value is not finite", {"metric": name}))
            elif result.kind in _BOUNDED_KINDS and not (0.0 - 1e-9 <= result.value <= 1.0 + 1e-9):
                findings.append(Finding("METRIC_OUT_OF_RANGE", Severity.WARNING,
                                        "metric value outside [0, 1]",
                                        {"metric": name, "value": result.value}))

    # 4) Version consistency.
    if versions.split_id != split_id:
        findings.append(Finding("VERSION_SPLIT_MISMATCH", Severity.WARNING,
                                "version bundle split_id does not match the split",
                                {"bundle": versions.split_id, "split": split_id}))
    if versions.metrics_version not in (None, METRICS_VERSION):
        findings.append(Finding("VERSION_METRICS_MISMATCH", Severity.WARNING,
                                "version bundle metrics_version differs from the runtime",
                                {"bundle": versions.metrics_version, "runtime": METRICS_VERSION}))
    if versions.evaluation_version != EVALUATION_VERSION:
        findings.append(Finding("VERSION_EVAL_MISMATCH", Severity.WARNING,
                                "version bundle evaluation_version differs from the runtime",
                                {"bundle": versions.evaluation_version, "runtime": EVALUATION_VERSION}))

    # 5) Artifact / benchmark consistency.
    if approval.approved and metric_results and not benchmark_present:
        findings.append(Finding("MISSING_BENCHMARK", Severity.WARNING,
                                "approved run with metrics but no benchmark recorded "
                                "(likely missing provenance)"))

    # 6) Lineage completeness.
    if lineage is None:
        findings.append(Finding("MISSING_LINEAGE", Severity.WARNING, "no evaluation lineage recorded"))
    elif not lineage.is_complete():
        findings.append(Finding("INCOMPLETE_LINEAGE", Severity.WARNING,
                                "evaluation lineage is missing required provenance",
                                {"missing": list(lineage.versions.missing_required())}))

    ok = not any(f.severity is Severity.CRITICAL for f in findings)
    return {
        "ok": ok,
        "findings": [f.to_dict() for f in findings],
        "checks": [
            "split_correctness", "leakage_absence", "metric_validity",
            "version_consistency", "artifact_consistency", "lineage_completeness",
        ],
    }
