"""Deterministic training manifests + environment/hardware capture.

The training manifest is the reproducibility contract for a run: it pins every
version coordinate, the training hyperparameters, the random seed, and the
environment so the run can be regenerated and audited (AP-6 / NR-10). The manifest
is canonical JSON, so its on-disk bytes (and checksum) are deterministic for a
fixed environment.
"""

from __future__ import annotations

import platform
import sys
from typing import Any

import numpy as np

from ..version import TRAINING_FRAMEWORK_VERSION
from ..lineage import VersionBundle


def environment_metadata() -> dict:
    """Capture the (pinned) software environment for reproducibility provenance."""
    return {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "implementation": platform.python_implementation(),
    }


def hardware_metadata() -> dict:
    """Capture coarse hardware metadata (recorded as provenance, not hashed into ids)."""
    return {
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "system": platform.system(),
    }


def build_training_manifest(
    *,
    model_config: Any,
    training_config: Any,
    version_bundle: VersionBundle,
    random_seed: int,
) -> dict:
    """Assemble the deterministic training manifest."""
    return {
        "training_framework_version": TRAINING_FRAMEWORK_VERSION,
        "version_bundle": version_bundle.to_dict(),
        "model_config": model_config.as_dict(),
        "training_config": training_config.as_dict(),
        "random_seed": random_seed,
        "optimizer": training_config.optimizer,
        "learning_rate": training_config.learning_rate,
        "batch_size": training_config.batch_size,
        "epochs": training_config.epochs,
        "environment": environment_metadata(),
        "hardware": hardware_metadata(),
    }
