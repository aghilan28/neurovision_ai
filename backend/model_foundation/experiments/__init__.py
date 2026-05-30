"""``backend/model_foundation/experiments`` — experiment tracking (P4-H).

Binds dataset + model + configuration + metrics + artifacts into a reproducible
``ExperimentRecord`` stored in an ``ExperimentRegistry``.
"""

from __future__ import annotations

from .tracker import build_experiment, ExperimentRegistry

__all__ = ["build_experiment", "ExperimentRegistry"]
