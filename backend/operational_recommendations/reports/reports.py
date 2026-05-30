"""Recommendation report builders (reproducible; version-tagged) (V3-P6).

Every report is a deterministic projection of already-derived recommendation
records and the registry/audit state. Reports add no new truth — they format
explainable recommendations for downstream human consumption.
"""

from __future__ import annotations

from typing import Any, Sequence

from ..version import RECOMMENDATION_REPORT_VERSION, OPERATIONAL_RECOMMENDATIONS_VERSION
from ..models.kinds import RecommendationKind


def _header(report_type: str, scope: str) -> dict:
    return {"report_type": report_type,
            "recommendation_report_version": RECOMMENDATION_REPORT_VERSION,
            "operational_recommendations_version": OPERATIONAL_RECOMMENDATIONS_VERSION,
            "scope": scope}


def _of_kind(records: Sequence, kind: str) -> list:
    return [r for r in records if r.kind == kind]


def _kind_report(report_type: str, records: Sequence, kind: str) -> dict:
    selected = _of_kind(records, kind)
    return {**_header(report_type, kind), "n_records": len(selected),
            "records": [r.to_dict() for r in selected]}


def build_guidance_report(records: Sequence) -> dict:
    return _kind_report("recommendation_guidance", records, RecommendationKind.GUIDANCE)


def build_priority_report(records: Sequence) -> dict:
    # priority report groups all records by priority level (explainable ordering)
    by_level: dict = {}
    for r in records:
        by_level.setdefault(r.priority.level, []).append(r.recommendation_id)
    return {**_header("recommendation_priority", "all"),
            "by_level": {lvl: sorted(ids) for lvl, ids in sorted(by_level.items())},
            "records": [{"recommendation_id": r.recommendation_id, "kind": r.kind,
                         "priority": r.priority.to_dict()} for r in records]}


def build_optimization_report(records: Sequence) -> dict:
    return _kind_report("recommendation_optimization", records, RecommendationKind.OPTIMIZATION)


def build_escalation_report(records: Sequence) -> dict:
    return _kind_report("recommendation_escalation", records, RecommendationKind.ESCALATION)


def build_recommendation_report(records: Sequence) -> dict:
    by_kind: dict = {}
    for r in records:
        by_kind.setdefault(r.kind, 0)
        by_kind[r.kind] += 1
    return {**_header("recommendation_summary", "operational"),
            "n_records": len(records), "by_kind": dict(sorted(by_kind.items())),
            "records": [r.to_dict() for r in records]}


def build_validation_report(scope: str, validation_report_dict: dict) -> dict:
    return {**_header("recommendation_validation", scope), "validation": validation_report_dict}


def build_audit_report(audit_log: Any) -> dict:
    return {**_header("recommendation_audit", "operational_recommendations"),
            "verified": audit_log.verify(), "audit": audit_log.to_dict()}
