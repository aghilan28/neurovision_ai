"""``evaluation.dataset_intelligence.statistics`` — deterministic summary statistics.

Pure, deterministic numeric helpers (NumPy-backed) used by the distribution and
profiling analyzers. No randomness, no wall-clock — identical inputs yield
identical statistics (AP-3/AP-6).
"""

from __future__ import annotations

from evaluation.dataset_intelligence.statistics.summaries import (
    category_counts,
    numeric_distribution,
    summarize,
)

__all__ = ["category_counts", "numeric_distribution", "summarize"]
