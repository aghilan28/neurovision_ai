"""``backend/inference_foundation/inference`` — model execution + prediction (P5-C/D).

``ModelExecutionEngine`` loads + verifies a trained model (deterministic reconstruction
via reproducibility) and runs validated execution; ``PredictionEngine`` builds the
structured, reproducible ``PredictionRecord``.
"""

from __future__ import annotations

from .execution import ModelExecutionEngine, ModelExecutionError
from .prediction import PredictionEngine, PredictionError

__all__ = ["ModelExecutionEngine", "ModelExecutionError", "PredictionEngine", "PredictionError"]
