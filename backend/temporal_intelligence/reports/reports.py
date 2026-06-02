"""Temporal report builders (reproducible; version-tagged) (V3-P2)."""

from __future__ import annotations

from typing import Any

from ..version import TEMPORAL_REPORT_VERSION, TEMPORAL_INTELLIGENCE_VERSION


def _header(report_type: str, scope: str) -> dict:
    return {"report_type": report_type, "temporal_report_version": TEMPORAL_REPORT_VERSION,
            "temporal_intelligence_version": TEMPORAL_INTELLIGENCE_VERSION, "scope": scope}


def build_timeline_report(timeline: Any) -> dict:
    t = timeline.to_dict()
    return {**_header("timeline", t["scope"]), "timeline": t}


def build_history_report(history: Any) -> dict:
    h = history.to_dict()
    return {**_header("history", h["scope"]), "history": h}


def build_evolution_report(evolution: Any) -> dict:
    e = evolution.to_dict()
    return {**_header("evolution", e["scope"]), "evolution": e}


def build_temporal_analytics_report(analytics: Any) -> dict:
    a = analytics.to_dict()
    return {**_header("temporal_analytics", a["scope"]), "analytics": a}


def build_validation_report(scope: str, validation_report_dict: dict) -> dict:
    return {**_header("temporal_validation", scope), "validation": validation_report_dict}


def build_audit_report(audit_log: Any) -> dict:
    return {**_header("temporal_audit", "temporal_intelligence"),
            "verified": audit_log.verify(), "audit": audit_log.to_dict()}


def build_lineage_report(artifact: Any, lineage_tracker: Any) -> dict:
    lid = getattr(artifact, "lineage_id", None)
    chain, verified = [], False
    if lid and lineage_tracker.exists(lid):
        chain = [r.to_dict() for r in lineage_tracker.chain(lid)]
        verified = lineage_tracker.verify_chain(lid)
    return {**_header("temporal_lineage", getattr(artifact, "scope", "")),
            "lineage_id": lid, "verified": verified,
            "chain_kinds": sorted({r["kind"] for r in chain}), "chain": chain}
