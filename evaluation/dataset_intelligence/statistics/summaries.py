"""Deterministic summary-statistics and distribution builders."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np

from evaluation.dataset_intelligence.schemas.common import (
    CategoryDistribution,
    NumericDistribution,
    SummaryStats,
)


def summarize(values: Sequence[float] | np.ndarray) -> SummaryStats:
    """Compute deterministic summary statistics for ``values`` (empty-safe)."""
    arr = np.asarray(list(values), dtype=np.float64)
    if arr.size == 0:
        return SummaryStats.empty()
    return SummaryStats(
        count=int(arr.size),
        total=float(np.sum(arr)),
        mean=float(np.mean(arr)),
        std=float(np.std(arr)),  # population std (ddof=0), deterministic
        minimum=float(np.min(arr)),
        p25=float(np.percentile(arr, 25)),
        median=float(np.percentile(arr, 50)),
        p75=float(np.percentile(arr, 75)),
        maximum=float(np.max(arr)),
    )


def numeric_distribution(
    name: str, values: Sequence[float] | np.ndarray, *, bins: int = 10
) -> NumericDistribution:
    """Build a :class:`NumericDistribution` (stats + fixed-edge histogram)."""
    arr = np.asarray(list(values), dtype=np.float64)
    stats = summarize(arr)
    if arr.size == 0 or bins < 1:
        return NumericDistribution(name=name, stats=stats)
    lo = float(np.min(arr))
    hi = float(np.max(arr))
    edges: tuple[float, ...]
    counts: tuple[int, ...]
    if hi <= lo:
        # Degenerate range: a single populated bin keeps the output deterministic.
        edges = (lo, lo + 1.0)
        counts = (int(arr.size),)
    else:
        counts_arr, edges_arr = np.histogram(arr, bins=bins, range=(lo, hi))
        edges = tuple(float(e) for e in edges_arr)
        counts = tuple(int(c) for c in counts_arr)
    return NumericDistribution(
        name=name, stats=stats, histogram_edges=edges, histogram_counts=counts
    )


def category_counts(name: str, items: Iterable[str]) -> CategoryDistribution:
    """Count categorical ``items`` deterministically (by count desc, then key asc)."""
    tally: dict[str, int] = {}
    for item in items:
        tally[item] = tally.get(item, 0) + 1
    ordered = tuple(sorted(tally.items(), key=lambda kv: (-kv[1], kv[0])))
    return CategoryDistribution(name=name, counts=ordered)
