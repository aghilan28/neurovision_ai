"""``backend/real_model_training/experiments`` — Experiment Tracking (T2-D).

Binds each training run to its reproducible coordinates: architecture, model version,
dataset version, feature version, configuration, hyperparameters, and the training /
evaluation / benchmark metrics — so every run is reproducible, traceable, and auditable.
"""

from __future__ import annotations

from ..identity import mint
from ..models.domain import Architecture, TrainingExperimentRecord
from ..version import (
    TRAINING_DATASET_VERSION, TRAINING_FEATURE_VERSION, DETERMINISTIC_EPOCH,
)


def build_experiment(*, architecture: Architecture, dataset_id: str, training_run_id: str,
                     model_id: str, configuration: dict, hyperparameters: dict,
                     training_metrics: dict, evaluation_metrics: dict, benchmark_metrics: dict,
                     reproducible: bool,
                     created_at: str = DETERMINISTIC_EPOCH) -> TrainingExperimentRecord:
    experiment_id = mint("rmt_experiment", {
        "architecture": architecture.value, "dataset_id": dataset_id,
        "training_run_id": training_run_id, "model_id": model_id})
    return TrainingExperimentRecord(
        experiment_id=experiment_id, architecture=architecture, dataset_id=dataset_id,
        dataset_version=TRAINING_DATASET_VERSION, feature_version=TRAINING_FEATURE_VERSION,
        training_run_id=training_run_id, model_id=model_id, configuration=dict(configuration),
        hyperparameters=dict(hyperparameters), training_metrics=dict(training_metrics),
        evaluation_metrics=dict(evaluation_metrics), benchmark_metrics=dict(benchmark_metrics),
        reproducible=reproducible, created_at=created_at)


__all__ = ["build_experiment"]
