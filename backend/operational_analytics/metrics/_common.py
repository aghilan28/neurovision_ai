"""Shared deterministic helpers for the analytics engines (V3-P5).

All analytics are reproducible numbers over already-derived inputs — no wall-clock,
no randomness. These helpers keep rounding and ratio computation consistent across
every engine so identical inputs always yield identical metrics.
"""

from __future__ import annotations

from typing import Sequence


SENTINEL_UNOBSERVED: float = -1.0


def rnd(x: float) -> float:
    """Deterministic 6-dp rounding that normalises ``-0.0`` to ``0.0``."""
    r = round(float(x), 6)
    return 0.0 if r == 0 else r


def ratio(numerator: float, denominator: float) -> float:
    """Bounded ratio in [0, inf); 0.0 when the denominator is 0 (unobserved)."""
    return rnd(numerator / denominator) if denominator else 0.0


def safe_ratio_0_1(numerator: float, denominator: float) -> float:
    """Ratio clamped to [0, 1]; 0.0 when the denominator is 0."""
    if not denominator:
        return 0.0
    return rnd(max(0.0, min(1.0, numerator / denominator)))


def mean(values: Sequence[float]) -> float:
    return rnd(sum(values) / len(values)) if values else 0.0


def clamp01(x: float) -> float:
    return rnd(max(0.0, min(1.0, x)))
