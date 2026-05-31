"""Training configuration + hyperparameter registry (DRP2-D).

Deterministic, versioned training configuration. The hyperparameter registry records the
default hyperparameters per production architecture so a training run is fully described
(and reproducible) by ``(architecture, seed, hyperparameters)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..models.domain import ProductionArchitecture
from ..version import DEFAULT_SEED

# Default hyperparameters per architecture (deterministic; callers may override).
# The reference-backed architectures inherit the model-foundation defaults; only training
# controls (epochs/lr/l2) and the hybrid's proj_dim are surfaced here.
HYPERPARAMETER_REGISTRY: dict[ProductionArchitecture, dict] = {
    ProductionArchitecture.EEGNET: {"epochs": 150, "lr": 0.1, "l2": 1e-3},
    ProductionArchitecture.DEEPCONVNET: {"epochs": 150, "lr": 0.1, "l2": 1e-3},
    ProductionArchitecture.TEMPORAL_CNN: {"epochs": 150, "lr": 0.1, "l2": 1e-3},
    ProductionArchitecture.TRANSFORMER_EEG: {"epochs": 150, "lr": 0.1, "l2": 1e-3},
    ProductionArchitecture.HYBRID_EEG: {"epochs": 150, "lr": 0.1, "l2": 1e-3, "proj_dim": 16},
}


@dataclass(frozen=True)
class TrainingConfig:
    """A deterministic, reproducible training configuration."""

    architecture: ProductionArchitecture
    seed: int = DEFAULT_SEED
    n_classes: int = 2
    val_fraction: float = 0.2
    test_fraction: float = 0.2
    hyperparameters: dict = field(default_factory=dict)

    def resolved_hyperparameters(self) -> dict:
        hp = dict(HYPERPARAMETER_REGISTRY.get(self.architecture, {}))
        hp.update(self.hyperparameters or {})
        return hp

    def signature(self) -> str:
        return hash_obj({
            "architecture": self.architecture.value, "seed": self.seed,
            "n_classes": self.n_classes, "val_fraction": self.val_fraction,
            "test_fraction": self.test_fraction,
            "hyperparameters": dict(sorted(self.resolved_hyperparameters().items())),
        })

    def to_dict(self) -> dict:
        return {
            "architecture": self.architecture.value, "seed": self.seed,
            "n_classes": self.n_classes, "val_fraction": self.val_fraction,
            "test_fraction": self.test_fraction,
            "hyperparameters": dict(sorted(self.resolved_hyperparameters().items())),
            "config_signature": self.signature(),
        }
