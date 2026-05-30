"""``backend/model_foundation/training`` — model architectures + deterministic training (P4-E/F).

Pure-NumPy deterministic baseline architectures (EEGNet / DeepConvNet / Temporal CNN /
Transformer) and a reproducible trainer that produces a ``TrainingRunRecord``.
"""

from __future__ import annotations

from .models import BaselineModel, build_model
from .trainer import train, TrainingError

__all__ = ["BaselineModel", "build_model", "train", "TrainingError"]
