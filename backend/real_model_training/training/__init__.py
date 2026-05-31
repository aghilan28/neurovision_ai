"""``backend/real_model_training/training`` — Model Training Framework (T2-C).

Trains the five platform architectures on the **real** windowed dataset by REUSING the
existing ``backend.production_models`` training engine (``train_production``) — no new
architecture and no duplicated training logic. Training is deterministic + reproducible
(the production trainer trains twice and compares parameter fingerprints) and registry/
dataset/feature-aware (it operates on the shared ``DatasetBundle``).
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.production_models.identity import mint_identity as prod_mint_identity
from backend.production_models.models.domain import ProductionArchitecture
from backend.production_models.training import TrainingConfig, train_production

from ..models.domain import Architecture
from ..version import DEFAULT_SEED, DETERMINISTIC_EPOCH

# Track-2 Architecture <-> production ProductionArchitecture (identical closed set).
_TO_PRODUCTION = {a: ProductionArchitecture(a.value) for a in Architecture}


@dataclass(frozen=True)
class TrainOutput:
    architecture: Architecture
    model_id: str
    training_run_id: str
    experiment_id: str
    params_fingerprint: str
    reproducible: bool
    training_time_ms: float
    train_metrics: dict
    n_params: int
    hyperparameters: dict
    model: object                       # the fitted reused model (not serialized)


def train_architecture(bundle, architecture: Architecture, *, seed: int = DEFAULT_SEED,
                       n_classes: int = 2, hyperparameters: dict | None = None,
                       created_at: str = DETERMINISTIC_EPOCH) -> TrainOutput:
    """Train one architecture on the real dataset (reuses ``train_production``)."""
    cfg = TrainingConfig(architecture=_TO_PRODUCTION[architecture], seed=seed, n_classes=n_classes,
                         hyperparameters=hyperparameters or {})
    tr = train_production(cfg, bundle, created_at=created_at)
    model_id = prod_mint_identity("production_model", {
        "training_run_id": tr.training_run_id, "model_key": tr.params_fingerprint}).id
    exp = tr.record
    return TrainOutput(
        architecture=architecture, model_id=model_id, training_run_id=tr.training_run_id,
        experiment_id=exp.experiment_id, params_fingerprint=tr.params_fingerprint,
        reproducible=tr.reproducible, training_time_ms=tr.training_time_ms,
        train_metrics=dict(exp.training_metrics), n_params=exp.n_params,
        hyperparameters=dict(exp.hyperparameters), model=tr.model)


__all__ = ["TrainOutput", "train_architecture"]
