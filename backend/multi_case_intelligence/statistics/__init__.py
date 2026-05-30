"""Deterministic statistical primitives for population analytics.

Pure functions only — no state, no wall-clock, no randomness. Every numeric
result is quantized so that identical inputs always hash identically.
"""

from backend.multi_case_intelligence.statistics import functions

__all__ = ["functions"]
