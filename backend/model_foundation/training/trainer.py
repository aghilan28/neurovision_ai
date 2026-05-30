"""Deterministic training foundation (P4-E).

Trains a baseline model on a dataset's train split and produces a reproducible
``TrainingRunRecord`` (hyperparameters, deterministic seed, training metrics +
history, content-addressed parameter fingerprint). The fitted model object is
returned alongside the record for evaluation; only the *fingerprint* is persisted.
"""

from __future__ import annotations

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..identity import mint_identity
from ..models.domain import ModelArchitecture, TrainingRunRecord
from ..version import DEFAULT_SEED, DETERMINISTIC_EPOCH
from .models import BaselineModel, build_model


class TrainingError(RuntimeError):
    """Raised when a training run cannot be executed."""


def train(architecture: ModelArchitecture, bundle, *, n_classes: int, seed: int = DEFAULT_SEED,
          hyperparameters: dict | None = None,
          created_at: str = DETERMINISTIC_EPOCH) -> tuple[TrainingRunRecord, BaselineModel]:
    """Train ``architecture`` on the dataset's train split; return (record, model)."""
    train_idx = bundle.split_indices("train")
    if train_idx.size == 0:
        raise TrainingError("empty training split")
    X_tr, y_tr = bundle.X[train_idx], bundle.y[train_idx]

    model = build_model(architecture, n_classes, seed=seed, hyperparameters=hyperparameters)
    model.fit(X_tr, y_tr)

    params_fp = model.params_fingerprint()
    training_key = hash_obj({
        "architecture": architecture.value, "seed": seed,
        "hyperparameters": model.hyperparameters, "params_fingerprint": params_fp,
        "n_train": int(train_idx.size)})
    identity = mint_identity("training_run", {
        "dataset_id": bundle.record.dataset_id, "training_key": training_key})

    training_metrics = {
        "final_loss": float(model.history[-1]["loss"]) if model.history else 0.0,
        "train_accuracy": float(model.train_accuracy), "n_train": int(train_idx.size),
        "n_epochs": int(model.hyperparameters["epochs"]),
    }
    record = TrainingRunRecord(
        training_run_id=identity.id, architecture=architecture, dataset_id=bundle.record.dataset_id,
        seed=seed, hyperparameters=model.hyperparameters,
        n_epochs=int(model.hyperparameters["epochs"]), training_metrics=training_metrics,
        training_history=tuple(model.history), params_fingerprint=params_fp,
        n_params=model.n_params(), created_at=created_at)
    return record, model
