"""``ml/training`` — the deterministic training framework (V1-P5).

Provides the reference training pipeline: a single, governed path that validates
inputs, trains a baseline deterministically, writes checksummed artifacts, records
lineage, registers the model, and emits a reproducible training report + manifest.
Every run is reproducible from its manifest (AP-6 / NR-10).
"""

from __future__ import annotations

from .config import TrainingConfig
from .manifest import build_training_manifest, environment_metadata, hardware_metadata
from .report import build_training_report
from .pipeline import Trainer, TrainingResult

__all__ = [
    "TrainingConfig",
    "build_training_manifest",
    "environment_metadata",
    "hardware_metadata",
    "build_training_report",
    "Trainer",
    "TrainingResult",
]
