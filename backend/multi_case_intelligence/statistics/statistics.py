"""Pure, deterministic statistical primitives for population analytics.

No state, no wall-clock, no randomness. Every numeric result is rounded to 6
decimals (the platform convention) so identical inputs always hash identically
(AP-3/AP-6, NR-9/NR-10).
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Callable, Mapping, Sequence

ROUND = 6


def _round(x: float) -> float:
    r = round(float(x), ROUND)
    return 0.0 if r == 0 else r  # normalize -0.0


def count(records: Sequence[object]) -> int:
    return len(records)


def distribution(records: Sequence[object], key_fn: Callable[[object], str]) -> dict:
    """Categorical distribution as ``{"counts": {cat: n}, "total": N}`` (sorted)."""
    counter: Counter[str] = Counter(str(key_fn(r)) for r in records)
    counts = {k: int(counter[k]) for k in sorted(counter)}
    return {"counts": counts, "total": int(sum(counter.values()))}


def coverage(records: Sequence[object], predicate: Callable[[object], bool]) -> dict:
    """Fraction of records satisfying ``predicate`` (defined ``0.0`` when empty)."""
    denom = len(records)
    num = sum(1 for r in records if predicate(r))
    ratio = _round(num / denom) if denom else 0.0
    return {"ratio": ratio, "numerator": int(num), "denominator": int(denom)}


def frequency(dist: Mapping[str, object]) -> dict:
    """Per-category relative frequency from a :func:`distribution` result."""
    total = int(dist["total"])
    counts = dist["counts"]
    if total == 0:
        return {k: 0.0 for k in counts}
    return {k: _round(n / total) for k, n in counts.items()}


def distinct_count(dist: Mapping[str, object]) -> int:
    return len(dist["counts"])


def normalized_entropy(dist: Mapping[str, object]) -> float:
    """Shannon entropy normalized to ``[0, 1]`` (0 = no spread, 1 = uniform)."""
    total = int(dist["total"])
    counts = list(dist["counts"].values())
    k = len(counts)
    if total == 0 or k <= 1:
        return 0.0
    entropy = 0.0
    for n in counts:
        if n <= 0:
            continue
        p = n / total
        entropy -= p * math.log(p, 2)
    return _round(entropy / math.log(k, 2))


def numeric_aggregates(values: Sequence[float]) -> dict:
    """Mean/min/max/n over numeric values (defined zeros when empty)."""
    vals = [float(v) for v in values if v is not None]
    if not vals:
        return {"mean": 0.0, "min": 0.0, "max": 0.0, "n": 0}
    return {"mean": _round(sum(vals) / len(vals)), "min": _round(min(vals)),
            "max": _round(max(vals)), "n": len(vals)}
