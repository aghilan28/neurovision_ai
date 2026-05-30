"""``backend/model_foundation/evaluation`` — deterministic evaluation engine (P4-G).

Pure-NumPy classification / calibration / uncertainty metrics and an evaluator that
produces a reproducible ``EvaluationRecord``.
"""

from __future__ import annotations

from . import metrics
from .evaluator import evaluate

__all__ = ["metrics", "evaluate"]
