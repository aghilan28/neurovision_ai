"""Pure, deterministic statistical functions.

These compute the building blocks of population analytics: counts,
distributions, coverage, variability, frequency, and confidence aggregates.
All are total functions over their inputs and contain no randomness or
wall-clock dependence, so any computed value is exactly reproducible.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Callable, Iterable, Mapping, Sequence

from backend.multi_case_intelligence.schemas.determinism import quantize
from backend.multi_case_intelligence.schemas.intelligence import Distribution


def count(records: Iterable[object]) -> int:
    """Number of records."""
    return sum(1 for _ in records)


def distribution(records: Sequence[object], field: str, key_fn: Callable[[object], str]) -> Distribution:
    """Categorical distribution over ``key_fn`` applied to each record.

    Counts are returned sorted by category for determinism.
    """
    counter: Counter[str] = Counter(str(key_fn(r)) for r in records)
    counts = tuple(sorted(counter.items(), key=lambda kv: kv[0]))
    return Distribution(field=field, counts=counts, total=sum(counter.values()))


def coverage(records: Sequence[object], predicate: Callable[[object], bool]) -> tuple[float, int, int]:
    """Fraction of records satisfying ``predicate``.

    Returns ``(ratio, numerator, denominator)``. An empty population has a
    defined coverage of ``0.0`` (with denominator ``0``) rather than raising.
    """
    denom = len(records)
    num = sum(1 for r in records if predicate(r))
    ratio = quantize(num / denom) if denom else 0.0
    return ratio, num, denom


def frequency(dist: Distribution) -> Mapping[str, float]:
    """Per-category relative frequency from a :class:`Distribution`."""
    total = dist.total
    if total == 0:
        return {category: 0.0 for category, _ in dist.counts}
    return {category: quantize(n / total) for category, n in dist.counts}


def distinct_count(dist: Distribution) -> int:
    """Number of distinct categories present."""
    return len(dist.counts)


def normalized_entropy(dist: Distribution) -> float:
    """Shannon entropy of the distribution normalized to ``[0, 1]``.

    ``0`` means all mass on one category (no variability); ``1`` means a uniform
    distribution over the observed categories (maximum variability). With 0 or 1
    categories the result is ``0.0`` by definition.
    """
    total = dist.total
    k = len(dist.counts)
    if total == 0 or k <= 1:
        return 0.0
    entropy = 0.0
    for _, n in dist.counts:
        if n <= 0:
            continue
        p = n / total
        entropy -= p * math.log(p, 2)
    return quantize(entropy / math.log(k, 2))


def confidence_aggregates(values: Sequence[float]) -> Mapping[str, float]:
    """Mean/min/max/count-with-value aggregates over confidence values.

    Missing confidences should simply be omitted by the caller. An empty input
    yields zeros (a defined, reproducible result).
    """
    if not values:
        return {"mean": 0.0, "min": 0.0, "max": 0.0, "n": 0.0}
    return {
        "mean": quantize(sum(values) / len(values)),
        "min": quantize(min(values)),
        "max": quantize(max(values)),
        "n": float(len(values)),
    }
