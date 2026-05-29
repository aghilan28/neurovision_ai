"""``ml/models`` — baseline model architectures (V1-P5).

Three modular, config-driven, versioned reference architectures:
  * ``SimpleCNN`` — a plain 1-D temporal CNN reference.
  * ``EEGNet``    — temporal + depthwise-spatial + separable convolutions.
  * ``TCN``       — a dilated causal temporal convolutional network.

Each architecture is a deterministic NumPy feature extractor (fixed, seeded
weights) followed by a *trainable* multinomial-logistic (softmax) head. This makes
the baselines bit-for-bit reproducible and framework-free (AP-3 / AP-6) — exactly
what reference baselines require, since the goal is reliability and reproducibility,
not peak accuracy. Future architectures (TCN-deep, Mamba, foundation models) are
compared against these.
"""

from __future__ import annotations

from .base import BaseModel, ModelConfig, TrainHistory
from .simple_cnn import SimpleCNN
from .eegnet import EEGNet
from .tcn import TCN
from .factory import build_model, available_models, ARCHITECTURE_REGISTRY

__all__ = [
    "BaseModel",
    "ModelConfig",
    "TrainHistory",
    "SimpleCNN",
    "EEGNet",
    "TCN",
    "build_model",
    "available_models",
    "ARCHITECTURE_REGISTRY",
]
