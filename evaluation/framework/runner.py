"""The evaluation orchestrator: gated, provenance-bound, auditable runs."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from evaluation._provenance import VersionBundle
from evaluation._version import EVALUATION_VERSION
from evaluation.benchmarking.builder import BenchmarkProvenanceError, build_benchmark_record
from evaluation.framework.schemas import EvaluationRun
from evaluation.lineage.tracker import build_evaluation_lineage
from evaluation.metrics.registry import METRICS_VERSION, MetricRegistry, default_metric_registry
from evaluation.metrics.schemas import MetricResult
from evaluation.registry.registry import EvaluationRegistry, RegisteredEvaluation
from evaluation.splits.schemas import SplitResult
from evaluation.validation.audit import audit_evaluation
from evaluation.validation.patient_disjoint import approve_split, validate_split

# Default metric suite for a classification benchmark (placeholders excluded).
_DEFAULT_METRICS = (
    "accuracy", "balanced_accuracy", "precision_macro", "recall_macro",
    "f1_macro", "confusion_matrix", "sensitivity_specificity",
)


@dataclass(frozen=True)
class Predictions:
    """Caller-supplied predictions for the evaluated partition.

    A stand-in for a future model's outputs — the framework computes *truth* from
    these, it does not produce them. ``y_score`` enables ranking metrics
    (AUROC/AUPRC); ``labels`` pins the label set for multiclass metrics.
    """

    y_true: np.ndarray
    y_pred: np.ndarray | None = None
    y_score: np.ndarray | None = None
    labels: tuple[int, ...] | None = None


def run_evaluation(
    split: SplitResult,
    predictions: Predictions,
    *,
    metric_names: Sequence[str] = _DEFAULT_METRICS,
    dataset_id: str | None = None,
    dataset_version: str | None = None,
    preprocessing_version: str | None = None,
    model_version: str | None = None,
    dataset_fingerprint: str | None = None,
    registry: MetricRegistry | None = None,
    evaluation_registry: EvaluationRegistry | None = None,
    created_at: str | None = None,
) -> EvaluationRun:
    """Run one gated, provenance-bound, auditable evaluation.

    Flow: validate split → **leakage gate** → (if approved) compute metrics →
    build a provenance-bound benchmark → record lineage → audit → register.
    If the split is not approved, **no metrics are computed and no benchmark is
    recorded** (NR-3); a blocked run is returned with the reason.
    """
    metric_registry = registry or default_metric_registry()

    split_validation = validate_split(split)
    approval = approve_split(split)

    versions = VersionBundle(
        evaluation_version=EVALUATION_VERSION,
        dataset_id=dataset_id or split.spec.dataset_id,
        dataset_version=dataset_version or split.spec.dataset_version,
        split_id=split.split_id,
        split_generator_version=split.spec.generator_version,
        preprocessing_version=preprocessing_version,
        metrics_version=METRICS_VERSION,
        model_version=model_version,
    )

    if not approval.approved:
        audit = audit_evaluation(
            versions=versions, split_id=split.split_id, split_validation=split_validation,
            approval=approval, metric_results={}, lineage=None, benchmark_present=False,
        )
        run = EvaluationRun(
            versions=versions, split_id=split.split_id,
            split_fingerprint=split.content_fingerprint, split_validation=split_validation,
            approval=approval, status="blocked", metric_results={}, benchmark=None,
            lineage=None, audit=audit, created_at=created_at,
        )
        _maybe_register(evaluation_registry, run)
        return run

    # --- approved: compute metrics ---
    metric_results: dict[str, MetricResult] = metric_registry.compute_suite(
        list(metric_names),
        y_true=predictions.y_true,
        y_pred=predictions.y_pred,
        y_score=predictions.y_score,
        labels=predictions.labels,
        skip_placeholders=True,
    )

    # --- benchmark (only with full provenance) ---
    benchmark = None
    try:
        benchmark = build_benchmark_record(
            versions, metric_results,
            split_fingerprint=split.content_fingerprint,
            dataset_fingerprint=dataset_fingerprint, created_at=created_at,
        )
    except BenchmarkProvenanceError:
        benchmark = None  # recorded as a finding by the audit

    # --- lineage ---
    artifact_fps = (benchmark.content_fingerprint,) if benchmark else ()
    lineage = build_evaluation_lineage(
        versions,
        split_population_fingerprint=split.population_fingerprint,
        split_fingerprint=split.content_fingerprint,
        metric_results=metric_results,
        result_artifact_fingerprints=artifact_fps,
        recorded_at=created_at,
    )

    audit = audit_evaluation(
        versions=versions, split_id=split.split_id, split_validation=split_validation,
        approval=approval, metric_results=metric_results, lineage=lineage,
        benchmark_present=benchmark is not None,
    )

    run = EvaluationRun(
        versions=versions, split_id=split.split_id,
        split_fingerprint=split.content_fingerprint, split_validation=split_validation,
        approval=approval, status="approved", metric_results=metric_results,
        benchmark=benchmark, lineage=lineage, audit=audit, created_at=created_at,
    )
    _maybe_register(evaluation_registry, run)
    return run


def _maybe_register(registry: EvaluationRegistry | None, run: EvaluationRun) -> None:
    if registry is None:
        return
    entry = RegisteredEvaluation(
        run_id=run.run_id,
        evaluation_version=run.versions.evaluation_version,
        versions=run.versions,
        split_id=run.split_id,
        metric_names=tuple(sorted(run.metric_results)),
        result_fingerprint=run.content_fingerprint,
        approved=run.approved,
        artifacts=((run.benchmark.benchmark_id,) if run.benchmark else ()),
        dependencies=tuple(
            v for v in (
                run.versions.dataset_version, run.versions.split_id,
                run.versions.preprocessing_version,
            ) if v
        ),
        status=run.status,
        created_at=run.created_at,
    )
    registry.register(entry, allow_replace=True)
