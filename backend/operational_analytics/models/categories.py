"""Analytics category vocabulary (V3-P5).

A closed, versioned set of analytics **categories** — the kinds of derived
operational intelligence the platform can produce. Every analytics record declares
a category from this set; the validator rejects anything else (category integrity).

The categories deliberately mirror the directive's engines (metrics, health,
performance, quality, trend, risk) plus a top-level ``operational`` summary. This
keeps the meaning of an analytics artifact stable and auditable.
"""

from __future__ import annotations

from ..version import ANALYTICS_CATEGORY_VERSION


class AnalyticsCategory:
    METRICS = "metrics"
    HEALTH = "health"
    PERFORMANCE = "performance"
    QUALITY = "quality"
    TREND = "trend"
    RISK = "risk"
    OPERATIONAL = "operational"     # the composite, platform-wide summary


ANALYTICS_CATEGORIES: frozenset[str] = frozenset(
    v for k, v in vars(AnalyticsCategory).items() if not k.startswith("_"))


class AnalyticsCategoryError(ValueError):
    """Raised when an analytics category is not in the closed vocabulary."""


def is_category(category: str) -> bool:
    return category in ANALYTICS_CATEGORIES


def validate_category(category: str) -> None:
    if not is_category(category):
        raise AnalyticsCategoryError(f"unknown analytics category {category!r}")


def categories() -> tuple[str, ...]:
    return tuple(sorted(ANALYTICS_CATEGORIES))


def to_dict() -> dict:
    return {"analytics_category_version": ANALYTICS_CATEGORY_VERSION,
            "n_categories": len(ANALYTICS_CATEGORIES),
            "categories": sorted(ANALYTICS_CATEGORIES)}
