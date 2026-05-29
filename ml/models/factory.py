"""Model factory — the single, governed entry point for constructing baselines.

Constructing models through one factory keeps the architecture registry explicit
and makes "no anonymous models" enforceable: the training pipeline and registry
only ever build models by name through here.
"""

from __future__ import annotations

from .base import BaseModel, ModelConfig
from .simple_cnn import SimpleCNN
from .eegnet import EEGNet
from .tcn import TCN

ARCHITECTURE_REGISTRY: dict[str, type[BaseModel]] = {
    SimpleCNN.name: SimpleCNN,
    EEGNet.name: EEGNet,
    TCN.name: TCN,
}


def available_models() -> list[str]:
    return sorted(ARCHITECTURE_REGISTRY)


def build_model(config: ModelConfig) -> BaseModel:
    """Construct (and deterministically initialize) a model from its config."""
    if config.name not in ARCHITECTURE_REGISTRY:
        raise ValueError(
            f"unknown architecture {config.name!r}; available: {available_models()}"
        )
    model = ARCHITECTURE_REGISTRY[config.name](config)
    model.initialize()
    return model
