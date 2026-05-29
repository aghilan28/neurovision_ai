"""``evaluation.reports`` — evaluation report assembly & persistence (V1-P4).

Builds the versioned reports the directive requires (evaluation, split, leakage,
benchmark, audit, summary) from an :class:`~evaluation.framework.schemas.EvaluationRun`,
and persists any report as canonical JSON (reproducible, diff-friendly).
"""

from __future__ import annotations

from evaluation.reports.generator import (
    audit_report,
    benchmark_report,
    evaluation_report,
    leakage_report,
    save_report,
    split_report,
    summary_report,
)

__all__ = [
    "audit_report",
    "benchmark_report",
    "evaluation_report",
    "leakage_report",
    "save_report",
    "split_report",
    "summary_report",
]
