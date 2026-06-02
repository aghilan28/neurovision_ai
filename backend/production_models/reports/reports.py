"""Production-model report builders (DRP2-J; reproducible, version-tagged).

Each report is a plain JSON-able dict, deterministic for a given record/registry state
(no wall-clock, no randomness — informational performance measures are reported but never
enter a signature). Mirrors the platform report style.
"""

from __future__ import annotations

from typing import Any, Optional

from ..version import PRODUCTION_REPORT_VERSION, PRODUCTION_MODELS_VERSION


def _header(report_type: str, model: Any) -> dict:
    return {
        "report_type": report_type,
        "production_report_version": PRODUCTION_REPORT_VERSION,
        "production_models_version": PRODUCTION_MODELS_VERSION,
        "model_id": model.model_id,
        "architecture": model.architecture.value,
        "dataset_id": model.dataset_id,
        "training_experiment_id": model.training_experiment_id,
        "benchmark_id": model.benchmark_id,
        "model_evaluation_id": model.model_evaluation_id,
        "readiness_id": model.readiness_id,
        "model_version": model.version.version,
    }


def build_training_report(model: Any, experiment: Any) -> dict:
    return {**_header("training", model), "training_experiment": experiment.to_dict()}


def build_benchmark_report(model: Any, benchmark: Any) -> dict:
    return {**_header("benchmark", model), "benchmark": benchmark.to_dict()}


def build_evaluation_report(model: Any, evaluation: Any) -> dict:
    return {**_header("evaluation", model), "evaluation": evaluation.to_dict()}


def build_comparison_report(comparison: dict) -> dict:
    return {
        "report_type": "comparison", "production_report_version": PRODUCTION_REPORT_VERSION,
        "production_models_version": PRODUCTION_MODELS_VERSION, "comparison": comparison,
    }


def build_readiness_report(model: Any, readiness: Any) -> dict:
    return {**_header("readiness", model), "readiness": readiness.to_dict()}


def build_registry_report(production_registry: Any, model_registry: Any,
                          dataset_registry: Any) -> dict:
    return {
        "report_type": "registry", "production_report_version": PRODUCTION_REPORT_VERSION,
        "production_models_version": PRODUCTION_MODELS_VERSION,
        "production_registry": production_registry.to_dict(),
        "shared_model_registry": model_registry.to_dict(),
        "shared_dataset_registry": dataset_registry.to_dict(),
    }


def build_audit_report(model: Any, audit_log: Any) -> dict:
    return {
        **_header("audit", model), "audit_head": audit_log.head,
        "chain_verified": audit_log.verify(), "n_events": len(audit_log),
        "events": [e.to_dict() for e in audit_log.events()],
    }


def build_lineage_report(model: Any, lineage_tracker: Any, readiness: Any) -> dict:
    chain_id = readiness.lineage_id or model.lineage_id
    chain = lineage_tracker.chain(chain_id) if chain_id else []
    return {
        **_header("lineage", model), "lineage_id": model.lineage_id,
        "readiness_lineage_id": readiness.lineage_id,
        "chain_verified": lineage_tracker.verify_chain(chain_id) if chain_id else False,
        "chain_length": len(chain), "chain_kinds": [r.kind for r in chain],
        "chain": [r.to_dict() for r in chain],
    }


def build_model_summary_report(model: Any, benchmark: Any, readiness: Any,
                               integrity_report: Optional[Any] = None) -> dict:
    out = {
        **_header("summary", model), "status": model.status.value,
        "readiness_class": model.readiness_class.value,
        "deterministic_metrics": dict(sorted(benchmark.deterministic_metrics.items())),
        "performance": dict(sorted(benchmark.performance.items())),
        "readiness_score": readiness.score,
        "content_validation_ok": model.validation.ok,
        "model": model.to_dict(),
    }
    if integrity_report is not None:
        out["integrity_validation"] = integrity_report.to_dict()
        out["ok"] = bool(model.validation.ok and integrity_report.ok)
    else:
        out["ok"] = bool(model.validation.ok)
    return out


__all__ = [
    "build_training_report", "build_benchmark_report", "build_evaluation_report",
    "build_comparison_report", "build_readiness_report", "build_registry_report",
    "build_audit_report", "build_lineage_report", "build_model_summary_report",
]
