"""Evaluation report builders + canonical-JSON persistence."""

from __future__ import annotations

import os
from typing import Any

from evaluation._canonical import canonical_json
from evaluation.framework.schemas import EvaluationRun
from evaluation.splits.schemas import SplitResult


def evaluation_report(run: EvaluationRun) -> dict[str, Any]:
    """The full evaluation report (the entire run)."""
    return run.to_dict()


def split_report(split: SplitResult) -> dict[str, Any]:
    """A split report (spec, partitions, fingerprints)."""
    return split.to_dict()


def leakage_report(run: EvaluationRun) -> dict[str, Any]:
    """The leakage verdict for the run's split."""
    return run.split_validation.leakage.to_dict()


def benchmark_report(run: EvaluationRun) -> dict[str, Any]:
    """The benchmark record (empty dict if none was recorded)."""
    return run.benchmark.to_dict() if run.benchmark else {}


def audit_report(run: EvaluationRun) -> dict[str, Any]:
    """The evaluation audit verdict."""
    return dict(run.audit)


def summary_report(run: EvaluationRun) -> dict[str, Any]:
    """A compact, headline summary of the run."""
    scalar_metrics = {
        name: result.value
        for name, result in run.metric_results.items()
        if result.value is not None
    }
    return {
        "run_id": run.run_id,
        "status": run.status,
        "approved": run.approved,
        "approval_reason": run.approval.reason,
        "split_id": run.split_id,
        "scheme": run.split_validation.scheme,
        "leakage_free": run.split_validation.leakage.leakage_free,
        "n_metrics": len(run.metric_results),
        "scalar_metrics": scalar_metrics,
        "benchmark_recorded": run.benchmark is not None,
        "audit_ok": bool(run.audit.get("ok", False)),
        "dataset_version": run.versions.dataset_version,
        "preprocessing_version": run.versions.preprocessing_version,
        "evaluation_version": run.versions.evaluation_version,
    }


def save_report(report: dict[str, Any], path: str | os.PathLike[str]) -> str:
    """Persist a report dict as canonical JSON; returns the path."""
    path = os.fspath(path)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(canonical_json(report))
    return path
