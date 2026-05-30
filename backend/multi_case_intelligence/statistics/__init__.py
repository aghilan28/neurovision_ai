"""Deterministic statistical primitives for population analytics (V2-P5)."""

from __future__ import annotations

from . import statistics
from .statistics import (
    count, distribution, coverage, frequency, distinct_count,
    normalized_entropy, numeric_aggregates,
)

__all__ = [
    "statistics", "count", "distribution", "coverage", "frequency",
    "distinct_count", "normalized_entropy", "numeric_aggregates",
]
