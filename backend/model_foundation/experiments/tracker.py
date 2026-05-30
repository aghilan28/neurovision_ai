"""Experiment tracking (P4-H).

Binds a dataset + model + configuration + metrics + artifacts into a reproducible
``ExperimentRecord`` and stores it in an ``ExperimentRegistry``. Every training run is
reproducible: the experiment captures the architecture, seed, hyperparameters, and the
content-addressed training/evaluation ids.
"""

from __future__ import annotations

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..identity import mint_identity
from ..models.domain import ExperimentRecord, ExperimentStatus, ModelArchitecture
from ..version import DETERMINISTIC_EPOCH, MODEL_EXPERIMENT_VERSION


def build_experiment(*, name: str, dataset_id: str, architecture: ModelArchitecture,
                     configuration: dict, training_run, evaluation, artifact_refs: tuple[str, ...],
                     status: ExperimentStatus = ExperimentStatus.COMPLETED,
                     created_at: str = DETERMINISTIC_EPOCH) -> ExperimentRecord:
    """Assemble a content-addressed ``ExperimentRecord``."""
    metrics = {
        "train_accuracy": training_run.training_metrics.get("train_accuracy", 0.0),
        "eval_accuracy": evaluation.metrics.get("accuracy", 0.0),
        "eval_f1_macro": evaluation.metrics.get("f1_macro", 0.0),
        "final_loss": training_run.training_metrics.get("final_loss", 0.0),
    }
    experiment_key = hash_obj({
        "name": name, "dataset_id": dataset_id, "architecture": architecture.value,
        "configuration": {k: configuration[k] for k in sorted(configuration)},
        "training_run_id": training_run.training_run_id, "evaluation_id": evaluation.evaluation_id})
    identity = mint_identity("experiment", {"dataset_id": dataset_id, "experiment_key": experiment_key})
    return ExperimentRecord(
        experiment_id=identity.id, name=name, dataset_id=dataset_id, architecture=architecture,
        configuration=configuration, training_run_id=training_run.training_run_id,
        evaluation_id=evaluation.evaluation_id, metrics=metrics, artifact_refs=tuple(artifact_refs),
        status=status, created_at=created_at)


class ExperimentRegistry:
    """In-memory experiment registry keyed by ``experiment_id``."""

    version = MODEL_EXPERIMENT_VERSION

    def __init__(self) -> None:
        self._records: dict[str, ExperimentRecord] = {}
        self._sigs: dict[str, str] = {}

    def register(self, record: ExperimentRecord) -> ExperimentRecord:
        sig = record.signature()
        if record.experiment_id in self._sigs and self._sigs[record.experiment_id] != sig:
            raise ValueError(
                f"experiment {record.experiment_id} already registered with different content "
                "(silent overwrite forbidden)")
        self._sigs[record.experiment_id] = sig
        self._records[record.experiment_id] = record
        return record

    def get(self, experiment_id: str) -> ExperimentRecord:
        if experiment_id not in self._records:
            raise KeyError(f"experiment {experiment_id!r} not in registry")
        return self._records[experiment_id]

    def exists(self, experiment_id: str) -> bool:
        return experiment_id in self._records

    def list_experiments(self) -> list[str]:
        return sorted(self._records)

    def to_dict(self) -> dict:
        return {
            "experiment_registry_version": self.version, "n_experiments": len(self._records),
            "experiments": {e: r.to_dict() for e, r in sorted(self._records.items())},
        }
