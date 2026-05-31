"""Deterministic identity generation for the Real Model Training subsystem (Track 2).

Content-addressed ``{kind}+{hash16}`` ids (the platform-wide scheme, NR-6), derived from
real content (dataset fingerprint, training run, evaluation/benchmark signatures) — never
from a wall-clock or a counter — so identical inputs reproduce identical ids.
"""

from __future__ import annotations

from typing import Mapping

from ml.provenance import content_id  # allowed: backend -> ml

_KINDS = ("training_dataset", "training_feature_asset", "training_recording", "trained_model",
          "model_evaluation_summary", "model_comparison", "rmt_experiment")


def mint(kind: str, payload: Mapping[str, object]) -> str:
    """Return a content-addressed id ``{kind}+{hash16}`` for ``payload``."""
    if kind not in _KINDS:
        raise ValueError(f"unknown identity kind {kind!r}")
    return content_id(kind, dict(payload))


__all__ = ["mint"]
