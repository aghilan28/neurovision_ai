"""Event workspace — registry, taxonomy, relationships, audit, lineage, reports."""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges
from ..visualizations import event_stream, event_category_distribution


def event_pages(state) -> list:
    block = state.events
    registry = block.get("registry", {})
    events = state.event_records
    reports = block.get("reports", {})
    taxonomy = block.get("taxonomy", {})
    audit = block.get("audit", {})

    summary_rows = [[e.get("event_type"), e.get("category"),
                     (e.get("source_entity_id") or "")[:16],
                     (e.get("event_id") or "")[:18], e.get("status"),
                     e.get("lineage_verified")]
                    for e in events[:40]]

    tax_categories = taxonomy.get("categories") or taxonomy.get("by_category") or {}
    tax_rows = ([[c, n] for c, n in sorted(tax_categories.items())]
                if isinstance(tax_categories, dict)
                else [[c, ""] for c in tax_categories])

    rel_report = reports.get("relationship_report", {})

    sections = [
        kv_panel("Event Registry", {
            "n_events": block.get("n_events"),
            "event_registry_version": registry.get("event_registry_version"),
            "audit_verified": audit.get("verified"),
        }),
        badges("Event Validation (representative)",
               [(c["name"], c["passed"])
                for c in block.get("representative_validation", {}).get("checks", [])]),
        table("Event Taxonomy", ["category", "n_event_types"], tax_rows),
        table("Events", ["type", "category", "source", "id", "status", "lineage_ok"],
              summary_rows),
        kv_panel("Event Relationships", {
            "n_relationships": rel_report.get("n_relationships", rel_report.get("n", 0)),
        }),
    ]
    viz = [event_stream(events), event_category_distribution(registry)]
    return [Page("events", "Events", sections, viz)]
