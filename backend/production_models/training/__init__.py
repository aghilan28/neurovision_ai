"""Production training program (DRP2-D)."""

from __future__ import annotations

from .config import HYPERPARAMETER_REGISTRY, TrainingConfig
from .trainer import TrainingError, TrainingResult, train_production

__all__ = [
    "HYPERPARAMETER_REGISTRY", "TrainingConfig", "TrainingError", "TrainingResult",
    "train_production",
]
