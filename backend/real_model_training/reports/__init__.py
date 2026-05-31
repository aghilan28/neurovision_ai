"""``backend/real_model_training/reports`` — deterministic Track-2 reports (T2-J).

Nine reports: Training, Evaluation, Benchmark, Comparison, Readiness, Registry, Audit,
Lineage, and Model Summary. Each is a pure function of the (already deterministic) records.
"""

from __future__ import annotations

from typing import Optional

from ..version import TRAINING_REPORT_VERSION


def _h(report_type: str) -> dict:
    return {"report_type": report_type, "rmt_report_version": TRAINING_REPORT_VERSION}


def build_training_report(dataset_record, experiments: list) -> dict:
    return {**_h("training"), "dataset": dataset_record.to_dict(),
            "n_experiments": len(experiments),
            "experiments": [e.to_dict() for e in experiments]}


def build_evaluation_report(evaluations: list) -> dict:
    return {**_h("evaluation"), "n_models": len(evaluations),
            "evaluations": [e.to_dict() for e in evaluations]}


def build_benchmark_report(benchmarks: list) -> dict:
    # Deterministic report: include the hashed deterministic metrics + the *names* of the
    # informational performance measures tracked (latency/memory/training-time/inference-time),
    # but NOT their wall-clock values (which legitimately vary run to run). The raw timings
    # remain available on each BenchmarkSummaryRecord.
    entries = []
    for b in benchmarks:
        entries.append({
            "benchmark_id": b.benchmark_id, "model_id": b.model_id,
            "architecture": b.architecture.value, "dataset_id": b.dataset_id, "split": b.split,
            "deterministic_metrics": {k: round(float(v), 9)
                                      for k, v in sorted(b.deterministic_metrics.items())},
            "performance_measures_tracked": sorted(b.performance.keys()),
            "n_samples": b.n_samples, "n_classes": b.n_classes,
            "metrics_signature": b.metrics_signature(),
            "benchmark_version": b.benchmark_version,
        })
    return {**_h("benchmark"), "n_models": len(benchmarks), "benchmarks": entries}


def build_comparison_report(comparison) -> dict:
    return {**_h("comparison"), "comparison": comparison.to_dict() if comparison else None}


def build_readiness_report(readinesses: list) -> dict:
    return {**_h("readiness"), "n_models": len(readinesses),
            "readiness": [r.to_dict() for r in readinesses]}


def build_registry_report(registry) -> dict:
    return {**_h("registry"), "counts": registry.counts(), "orphans": registry.orphans(),
            "n_records": registry.to_dict()["n_records"]}


def build_audit_report(audit_log, *, subject: str) -> dict:
    return {**_h("audit"), "subject": subject, "audit_head": audit_log.head,
            "chain_verified": audit_log.verify(), "n_events": len(audit_log),
            "events": [e.to_dict() for e in audit_log.events()]}


def build_lineage_report(tracker, lineage_id: Optional[str]) -> dict:
    chain = tracker.chain(lineage_id) if lineage_id else []
    return {**_h("lineage"), "lineage_id": lineage_id,
            "chain_verified": tracker.verify_chain(lineage_id) if lineage_id else False,
            "chain_length": len(chain), "chain_kinds": sorted({r.kind for r in chain}),
            "chain": [r.to_dict() for r in chain]}


def build_model_summary_report(candidate) -> dict:
    return {**_h("model_summary"), "model_id": candidate.model_id,
            "architecture": candidate.architecture.value,
            "readiness_class": candidate.readiness_class.value,
            "ready_for_serving": candidate.ready_for_serving,
            "headline_metrics": candidate.to_dict()["headline_metrics"],
            "model": candidate.to_dict()}


__all__ = [
    "build_training_report", "build_evaluation_report", "build_benchmark_report",
    "build_comparison_report", "build_readiness_report", "build_registry_report",
    "build_audit_report", "build_lineage_report", "build_model_summary_report",
]
