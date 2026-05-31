"""Production benchmarking program (DRP2-E)."""

from __future__ import annotations

from . import metrics
from .benchmarker import benchmark_model

__all__ = ["metrics", "benchmark_model"]
