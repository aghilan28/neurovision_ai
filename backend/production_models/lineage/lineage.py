"""Production-model lineage helpers built on the shared ``ml.lineage`` machinery (DRP2-I).

No parallel lineage system: training-experiment / production-model / benchmark /
readiness-assessment nodes are recorded in the *same* ``ml.lineage.LineageTracker`` as
every upstream node, reusing the model-foundation dataset / training-run / evaluation
helpers for the lower chain. The nodes are wired so a single ``verify_chain`` from a
readiness assessment reaches the patient:

    Patient -> Case -> EEG -> Processed -> Feature -> Dataset -> Training Run ->
    Training Experiment -> Model -> Benchmark -> Readiness Assessment

(the evaluation node also parents the training-run node and is referenced by the
benchmark node), connecting a production-candidate model's readiness back to the patient
with complete traceability.
"""

from __future__ import annotations

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

# Reuse the model-foundation lower-chain helpers (no duplication).
from backend.model_foundation import (
    make_dataset_lineage, make_training_lineage, make_evaluation_lineage,
)

from ..version import (
    PRODUCTION_MODELS_VERSION, PRODUCTION_DOMAIN_VERSION, PRODUCTION_IDENTITY_VERSION,
    PRODUCTION_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)

__all__ = [
    "make_dataset_lineage", "make_training_lineage", "make_evaluation_lineage",
    "make_training_experiment_lineage", "make_production_model_lineage",
    "make_benchmark_lineage", "make_readiness_lineage", "production_version_bundle",
]


def production_version_bundle(**extra: object) -> dict:
    bundle = {
        "production_models_version": PRODUCTION_MODELS_VERSION,
        "production_domain_version": PRODUCTION_DOMAIN_VERSION,
        "production_identity_version": PRODUCTION_IDENTITY_VERSION,
        "production_lineage_version": PRODUCTION_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_training_experiment_lineage(experiment_id: str, training_lineage_id: str, *,
                                     architecture: str,
                                     created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A training-experiment lineage node parented on the training-run node."""
    return make_lineage_record(
        kind="training_experiment", versions=production_version_bundle(),
        inputs={"training_run_id": training_lineage_id, "architecture": architecture},
        outputs={"training_experiment_id": experiment_id}, parents=(training_lineage_id,),
        created_at=created_at)


def make_production_model_lineage(model_id: str, experiment_lineage_id: str, *, architecture: str,
                                  params_fingerprint: str,
                                  created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A production-model lineage node parented on the training-experiment node."""
    return make_lineage_record(
        kind="model", versions=production_version_bundle(),
        inputs={"training_experiment_id": experiment_lineage_id, "architecture": architecture},
        outputs={"model_id": model_id, "params_fingerprint": params_fingerprint},
        parents=(experiment_lineage_id,), created_at=created_at)


def make_benchmark_lineage(benchmark_id: str, model_lineage_id: str, evaluation_lineage_id: str, *,
                           metrics_signature: str,
                           created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A benchmark lineage node parented on the model node + the evaluation node."""
    return make_lineage_record(
        kind="benchmark", versions=production_version_bundle(),
        inputs={"model_id": model_lineage_id, "evaluation_id": evaluation_lineage_id},
        outputs={"benchmark_id": benchmark_id, "metrics_signature": metrics_signature},
        parents=(model_lineage_id, evaluation_lineage_id), created_at=created_at)


def make_readiness_lineage(readiness_id: str, benchmark_lineage_id: str, *, classification: str,
                           created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A readiness-assessment lineage node parented on the benchmark node."""
    return make_lineage_record(
        kind="readiness_assessment", versions=production_version_bundle(),
        inputs={"benchmark_id": benchmark_lineage_id},
        outputs={"readiness_id": readiness_id, "classification": classification},
        parents=(benchmark_lineage_id,), created_at=created_at)
