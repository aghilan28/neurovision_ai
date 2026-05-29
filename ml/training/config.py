"""Training configuration (the directive's 'Training Configuration').

Captures every parameter that affects a training run so the run is reproducible
and auditable. Version coordinates (dataset/split/preprocessing/model) are bound
in the manifest at run time; this config holds the optimizer hyperparameters,
seed, and ownership.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

from ..version import TRAINING_FRAMEWORK_VERSION
from ..provenance import hash_obj


@dataclass(frozen=True)
class TrainingConfig:
    optimizer: str = "full_batch_gradient_descent"
    learning_rate: float = 0.5
    l2: float = 1e-3
    steps: int = 300
    seed: int = 0
    owner: str = "neurovision-ml"

    def __post_init__(self) -> None:
        if self.steps <= 0:
            raise ValueError("steps must be positive")
        if self.learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        if self.l2 < 0:
            raise ValueError("l2 must be non-negative")

    @property
    def epochs(self) -> int:
        # full-batch GD: one optimization step processes the whole training set,
        # so steps == epochs by construction.
        return self.steps

    @property
    def batch_size(self) -> str:
        return "full"

    def as_dict(self) -> dict:
        d = asdict(self)
        d.update({
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "training_framework_version": TRAINING_FRAMEWORK_VERSION,
        })
        return d

    def signature(self) -> str:
        return hash_obj(self.as_dict())
