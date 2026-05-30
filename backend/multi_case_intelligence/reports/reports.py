"""Intelligence report builders (reproducible; version-tagged) (V2-P5)."""

from __future__ import annotations

from typing import Any

from ..version import INTEL_REPORT_VERSION, MULTI_CASE_INTELLIGENCE_VERSION


def _header(report_type: str, scope: str) -> dict:
    return {"report_type": report_type, "intel_report_version": INTEL_REPORT_VERSION,
            "multi_case_intelligence_version": MULTI_CASE_INTELLIGENCE_VERSION, "scope": scope}


def build_cohort_report(cohort: Any) -> dict:
    return {**_header("cohort", f"cohort:{cohort.cohort_id}"),
            "cohort_id": cohort.cohort_id, "member_kind": cohort.member_kind,
            "size": cohort.size, "definition": cohort.definition.to_dict(),
            "members": list(cohort.members), "version": cohort.version,
            "lineage_id": cohort.lineage_id}


def build_analytics_report(analytics: Any) -> dict:
    return {**_header("analytics", analytics.scope), "analytics_id": analytics.analytics_id,
            "cohort_id": analytics.cohort_id, "version": analytics.version,
            "lineage_id": analytics.lineage_id,
            "blocks": [b.to_dict() for b in analytics.blocks]}


def build_trend_report(trend: Any) -> dict:
    return {**_header("trend", trend.scope), "trend_id": trend.trend_id,
            "version": trend.version, "lineage_id": trend.lineage_id,
            "series": [s.to_dict() for s in trend.series]}


def build_quality_report(quality: Any) -> dict:
    return {**_header("quality", quality.scope), "quality_id": quality.quality_id,
            "version": quality.version, "lineage_id": quality.lineage_id,
            "metrics": [m.to_dict() for m in quality.metrics]}


def build_population_report(analytics: Any, trend: Any, quality: Any) -> dict:
    return {
        **_header("population", analytics.scope),
        "population_counts": {b.subject_kind: b.count for b in analytics.blocks},
        "quality": {m.name: m.value for m in quality.metrics},
        "trend_directions": {s.metric: s.direction for s in trend.series},
        "references": {"analytics_id": analytics.analytics_id, "trend_id": trend.trend_id,
                       "quality_id": quality.quality_id},
    }


def build_validation_report(scope: str, validation_report_dict: dict) -> dict:
    return {**_header("validation", scope), "validation": validation_report_dict}


def build_registry_report(registry: Any) -> dict:
    return {**_header("registry", "intelligence"), "registry": registry.to_dict()}
