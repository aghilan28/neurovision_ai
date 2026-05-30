"""Model-foundation report builders (reproducible; version-tagged).

Each report is a plain JSON-able dict, deterministic for a given record/registry
state (no wall-clock, no randomness). Mirrors the platform report style.
"""

from __future__ import annotations

from typing import Any, Optional

from ..version import MODEL_REPORT_VERSION, MODEL_FOUNDATION_VERSION


def _header(report_type: str, model: Any) -> dict:
    return {
        "report_type": report_type,
        "model_report_version": MODEL_REPORT_VERSION,
        "model_foundation_version": MODEL_FOUNDATION_VERSION,
        "model_id": model.model_id,
        "dataset_id": model.dataset_id,
        "training_run_id": model.training_run_id,
        "evaluation_id": model.evaluation_id,
        "experiment_id": model.experiment_id,
        "case_id": model.case_id,
        "model_version": model.version.version,
    }


def build_dataset_report(model: Any, dataset_record: Any) -> dict:
    return {**_header("dataset", model), "dataset": dataset_record.to_dict()}


def build_training_report(model: Any, training_run: Any) -> dict:
    return {**_header("training", model), "training_run": training_run.to_dict()}


def build_evaluation_report(model: Any, evaluation: Any) -> dict:
    return {**_header("evaluation", model), "evaluation": evaluation.to_dict()}


def build_experiment_report(model: Any, experiment: Any) -> dict:
    return {**_header("experiment", model), "experiment": experiment.to_dict()}


def build_model_report(model: Any) -> dict:
    return {**_header("model", model), "model": model.to_dict()}


def build_audit_report(model: Any, audit_log: Any) -> dict:
    return {
        **_header("audit", model), "audit_head": audit_log.head,
        "chain_verified": audit_log.verify(), "n_events": len(audit_log),
        "events": [e.to_dict() for e in audit_log.events()],
    }


def build_lineage_report(model: Any, lineage_tracker: Any) -> dict:
    chain = lineage_tracker.chain(model.lineage_id) if model.lineage_id else []
    return {
        **_header("lineage", model), "lineage_id": model.lineage_id,
        "chain_verified": lineage_tracker.verify_chain(model.lineage_id) if model.lineage_id else False,
        "chain_length": len(chain), "chain_kinds": [r.kind for r in chain],
        "chain": [r.to_dict() for r in chain],
    }


def build_validation_report(model: Any, integrity_report: Optional[Any] = None) -> dict:
    out = {**_header("validation", model), "content_validation": model.validation.to_dict()}
    if integrity_report is not None:
        out["integrity_validation"] = integrity_report.to_dict()
        out["ok"] = bool(model.validation.ok and integrity_report.ok)
    else:
        out["ok"] = bool(model.validation.ok)
    return out


def build_dataset_registry_report(dataset_registry: Any) -> dict:
    return {
        "report_type": "registry", "model_report_version": MODEL_REPORT_VERSION,
        "model_foundation_version": MODEL_FOUNDATION_VERSION,
        "datasets": dataset_registry.to_dict(),
    }


def build_registry_report(model_registry: Any, dataset_registry: Any,
                          experiment_registry: Any) -> dict:
    return {
        "report_type": "registry", "model_report_version": MODEL_REPORT_VERSION,
        "model_foundation_version": MODEL_FOUNDATION_VERSION,
        "n_models": len(model_registry.list_models()), "models": model_registry.to_dict(),
        "datasets": dataset_registry.to_dict(), "experiments": experiment_registry.to_dict(),
    }
