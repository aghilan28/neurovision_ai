"""Analytics report builders (reproducible; version-tagged) (V3-P5).

Every report is a deterministic projection of already-derived analytics records and
the registry/audit/lineage state. Reports add no new truth — they format derived
intelligence for downstream consumers (e.g. the V3-P6 recommendation layer).
"""

from __future__ import annotations

from typing import Any, Sequence

from ..version import ANALYTICS_REPORT_VERSION, OPERATIONAL_ANALYTICS_VERSION
from ..models.categories import AnalyticsCategory


def _header(report_type: str, scope: str) -> dict:
    return {"report_type": report_type, "analytics_report_version": ANALYTICS_REPORT_VERSION,
            "operational_analytics_version": OPERATIONAL_ANALYTICS_VERSION, "scope": scope}


def _records_of(records: Sequence, category: str) -> list:
    return [r for r in records if r.category == category]


def _dimension_report(report_type: str, records: Sequence, category: str) -> dict:
    selected = _records_of(records, category)
    return {**_header(report_type, category),
            "n_records": len(selected),
            "records": [r.to_dict() for r in selected]}


def build_metrics_report(records: Sequence) -> dict:
    return _dimension_report("analytics_metrics", records, AnalyticsCategory.METRICS)


def build_health_report(records: Sequence) -> dict:
    return _dimension_report("analytics_health", records, AnalyticsCategory.HEALTH)


def build_performance_report(records: Sequence) -> dict:
    return _dimension_report("analytics_performance", records, AnalyticsCategory.PERFORMANCE)


def build_quality_report(records: Sequence) -> dict:
    return _dimension_report("analytics_quality", records, AnalyticsCategory.QUALITY)


def build_trend_report(records: Sequence) -> dict:
    return _dimension_report("analytics_trend", records, AnalyticsCategory.TREND)


def build_risk_report(records: Sequence) -> dict:
    return _dimension_report("analytics_risk", records, AnalyticsCategory.RISK)


def build_analytics_summary_report(records: Sequence) -> dict:
    by_category: dict = {}
    for r in records:
        by_category.setdefault(r.category, 0)
        by_category[r.category] += 1
    operational = _records_of(records, AnalyticsCategory.OPERATIONAL)
    return {**_header("analytics_summary", "operational"),
            "n_records": len(records),
            "by_category": dict(sorted(by_category.items())),
            "operational": [r.to_dict() for r in operational]}


def build_validation_report(scope: str, validation_report_dict: dict) -> dict:
    return {**_header("analytics_validation", scope), "validation": validation_report_dict}


def build_audit_report(audit_log: Any) -> dict:
    return {**_header("analytics_audit", "operational_analytics"),
            "verified": audit_log.verify(), "audit": audit_log.to_dict()}
