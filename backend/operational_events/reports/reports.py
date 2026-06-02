"""Event report builders (reproducible; version-tagged) (V3-P1)."""

from __future__ import annotations

from typing import Any

from ..version import EVENT_REPORT_VERSION, OPERATIONAL_EVENTS_VERSION
from .. import taxonomy as taxonomy_mod


def _header(report_type: str, scope: str) -> dict:
    return {"report_type": report_type, "event_report_version": EVENT_REPORT_VERSION,
            "operational_events_version": OPERATIONAL_EVENTS_VERSION, "scope": scope}


def build_event_summary_report(registry: Any) -> dict:
    by_category: dict = {}
    by_type: dict = {}
    for eid in registry.list_events():
        rec = registry.get(eid)
        by_category[rec.category] = by_category.get(rec.category, 0) + 1
        by_type[rec.event_type] = by_type.get(rec.event_type, 0) + 1
    return {**_header("event_summary", "operational_events"),
            "n_events": len(registry.list_events()), "n_active": len(registry.active()),
            "by_category": dict(sorted(by_category.items())),
            "by_type": dict(sorted(by_type.items()))}


def build_event_taxonomy_report() -> dict:
    return {**_header("event_taxonomy", "taxonomy"), "taxonomy": taxonomy_mod.to_dict()}


def build_event_registry_report(registry: Any) -> dict:
    return {**_header("event_registry", "operational_events"), "registry": registry.to_dict()}


def build_relationship_report(registry: Any) -> dict:
    rels = [registry.relationship(rid).to_dict() for rid in registry.list_relationships()]
    by_relation: dict = {}
    for r in rels:
        by_relation[r["relation"]] = by_relation.get(r["relation"], 0) + 1
    return {**_header("event_relationship", "operational_events"),
            "n_relationships": len(rels), "by_relation": dict(sorted(by_relation.items())),
            "relationships": rels}


def build_event_validation_report(scope: str, validation_report_dict: dict) -> dict:
    return {**_header("event_validation", scope), "validation": validation_report_dict}


def build_event_audit_report(audit_log: Any) -> dict:
    return {**_header("event_audit", "operational_events"),
            "verified": audit_log.verify(), "audit": audit_log.to_dict()}


def build_event_lineage_report(event, lineage_tracker: Any) -> dict:
    chain = []
    verified = False
    if event.lineage_id and lineage_tracker.exists(event.lineage_id):
        chain = [r.to_dict() for r in lineage_tracker.chain(event.lineage_id)]
        verified = lineage_tracker.verify_chain(event.lineage_id)
    return {**_header("event_lineage", event.event_id),
            "event_id": event.event_id, "lineage_id": event.lineage_id,
            "verified": verified, "chain_kinds": sorted({r["kind"] for r in chain}),
            "chain": chain}
