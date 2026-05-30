"""Analytics domain model package (V3-P5)."""

from __future__ import annotations

from .categories import (
    AnalyticsCategory, AnalyticsCategoryError, ANALYTICS_CATEGORIES,
    is_category, validate_category, categories,
)
from .domain import (
    AnalyticsMetric, AnalyticsSourceRef, AnalyticsRecord,
    AnalyticsAuditRecord, AnalyticsVersion, AnalyticsLineageRecord, AnalyticsRegistryRecord,
)

__all__ = [
    "AnalyticsCategory", "AnalyticsCategoryError", "ANALYTICS_CATEGORIES",
    "is_category", "validate_category", "categories",
    "AnalyticsMetric", "AnalyticsSourceRef", "AnalyticsRecord",
    "AnalyticsAuditRecord", "AnalyticsVersion", "AnalyticsLineageRecord",
    "AnalyticsRegistryRecord",
]
