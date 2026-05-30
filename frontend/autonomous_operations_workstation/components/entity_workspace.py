"""Shared builder for an entity workspace page (V4-P8) — stdlib only (NR-8).

Goals, policies, plans, tasks, agents, and executions all present the same shape:
a registry summary, a record table (state + governance + version + lineage), a
governance-state badge strip, an audit-integrity badge, and the registered reports
that subsystem exposes. This builder produces that page so each workspace stays a
thin, declarative wrapper. Everything shown comes from the snapshot's registered
artifacts; nothing is recomputed.
"""

from __future__ import annotations

from ..schemas import Page
from .components import kv_panel, table, badges, bar_chart


def _approval_field(record: dict) -> str:
    return record.get("authorization_state") or record.get("approval_state") or ""


def _state_distribution(records: list) -> dict:
    dist: dict = {}
    for r in records:
        dist[r.get("state", "")] = dist.get(r.get("state", ""), 0) + 1
    return dict(sorted(dist.items()))


def entity_pages(state, *, block: str, page_id: str, title: str, id_label: str,
                 extra_columns: list | None = None, controls: list | None = None) -> list:
    """Build the standard one-page workspace for a governed-entity ``block``."""
    b = state.block(block)
    records = state.records(block)
    registry = b.get("registry", {})
    audit = b.get("audit", {})
    reports = b.get("reports", {})

    extra_columns = extra_columns or []
    columns = [id_label, "state", "governance", "version", "lineage"] + \
        [c[0] for c in extra_columns]
    rows = []
    for r in records:
        row = [(r.get("id", "") or "")[:18], r.get("state", ""), _approval_field(r),
               (r.get("version", "") or "")[:10], r.get("lineage_verified", False)]
        for _, fn in extra_columns:
            row.append(fn(r))
        rows.append(row)

    dist = _state_distribution(records)
    summary = kv_panel(f"{title} Summary", {
        "n_records": len(records),
        "n_registered": registry.get(f"n_{block}", registry.get("n_records", len(records))),
        "audit_verified": audit.get("verified", False),
        "all_lineage_verified": all(r.get("lineage_verified", False) for r in records)
        if records else True,
        "reports": sorted(reports.keys()),
    })
    sections = [
        summary,
        badges(f"{title} Governance",
               [((r.get("id", "") or "")[:14], _approval_field(r) in ("approved", "authorized"))
                for r in records]),
        badges(f"{title} Lineage Integrity",
               [((r.get("id", "") or "")[:14], r.get("lineage_verified", False))
                for r in records]),
        table(f"{title} Registry", columns, rows),
    ]
    viz = [bar_chart(f"{title} by State", list(dist.keys()), list(dist.values()))]
    return [Page(page_id, title, sections, viz, controls or [])]
