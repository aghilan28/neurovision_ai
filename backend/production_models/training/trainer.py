"""Deterministic production training program (DRP2-D).

Trains a production-candidate architecture on a dataset's train split and produces a
reproducible :class:`TrainingExperimentRecord` (hyperparameters, deterministic seed,
training metrics + history, content-addressed parameter fingerprint, reproducibility
flag). The fitted model object is returned alongside the record for evaluation +
benchmarking; only the *fingerprint* is persisted (never raw weights).

Reproducibility is *verified*, not assumed: the architecture is trained twice and the
parameter fingerprints are compared. ``training_time_ms`` is captured but is **informational
only** — it never enters any signature (NR-9/NR-10).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from ml.provenance import hash_obj  # allowed: backend -> ml
from backend.model_foundation import mint_identity as mint_foundation_identity  # reuse identity

from ..architectures import build_production_model
from ..identity import mint_identity
from ..models.domain import ExperimentStatus, TrainingExperimentRecord
from ..version import DETERMINISTIC_EPOCH
from .config import TrainingConfig


class TrainingError(RuntimeError):
    """Raised when a production training run cannot be executed."""


@dataclass(frozen=True)
class TrainingResult:
    """A completed training run: the record, the fitted model, and the minted ids."""

    record: TrainingExperimentRecord
    model: object
    training_run_id: str
    params_fingerprint: str
    reproducible: bool
    training_time_ms: float


def train_production(config: TrainingConfig, bundle, *,
                     created_at: str = DETERMINISTIC_EPOCH) -> TrainingResult:
    """Train ``config.architecture`` on the dataset's train split; return a result."""
    train_idx = bundle.split_indices("train")
    if train_idx.size == 0:
        raise TrainingError("empty training split")
    X_tr, y_tr = bundle.X[train_idx], bundle.y[train_idx]
    hp = config.resolved_hyperparameters()

    t0 = time.perf_counter()
    model = build_production_model(config.architecture, config.n_classes, seed=config.seed,
                                   hyperparameters=hp)
    model.fit(X_tr, y_tr)
    training_time_ms = (time.perf_counter() - t0) * 1000.0

    params_fp = model.params_fingerprint()

    # --- verify reproducibility (train again; compare fingerprints) -----------
    model2 = build_production_model(config.architecture, config.n_classes, seed=config.seed,
                                    hyperparameters=hp)
    model2.fit(X_tr, y_tr)
    reproducible = (params_fp == model2.params_fingerprint())

    # --- mint the reused training_run id + the production experiment id -------
    training_key = hash_obj({
        "architecture": config.architecture.value, "seed": config.seed,
        "hyperparameters": dict(sorted(hp.items())), "params_fingerprint": params_fp,
        "n_train": int(train_idx.size)})
    training_run_id = mint_foundation_identity(
        "training_run", {"dataset_id": bundle.record.dataset_id, "training_key": training_key}).id

    experiment_key = hash_obj({
        "architecture": config.architecture.value, "config": config.signature(),
        "params_fingerprint": params_fp})
    experiment_id = mint_identity(
        "training_experiment", {"training_run_id": training_run_id, "experiment_key": experiment_key}).id

    training_metrics = {
        "final_loss": float(model.history[-1]["loss"]) if model.history else 0.0,
        "train_accuracy": float(model.train_accuracy), "n_train": int(train_idx.size),
        "n_epochs": int(hp.get("epochs", 0)),
    }
    record = TrainingExperimentRecord(
        experiment_id=experiment_id, architecture=config.architecture,
        dataset_id=bundle.record.dataset_id, training_run_id=training_run_id, seed=config.seed,
        hyperparameters=hp, n_epochs=int(hp.get("epochs", 0)), training_metrics=training_metrics,
        training_history=tuple(model.history), params_fingerprint=params_fp,
        n_params=model.n_params(), reproducible=reproducible,
        status=ExperimentStatus.COMPLETED if reproducible else ExperimentStatus.QUARANTINED,
        created_at=created_at)
    return TrainingResult(record=record, model=model, training_run_id=training_run_id,
                          params_fingerprint=params_fp, reproducible=reproducible,
                          training_time_ms=training_time_ms)
