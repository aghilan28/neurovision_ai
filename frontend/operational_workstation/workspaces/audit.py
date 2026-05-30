"""Audit workspace — a unified browser over every V3 immutable audit log."""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges
from ..visualizations import audit_timeline, version_history


def audit_pages(state) -> list:
    logs = state.audit_logs()                 # list[(scope, audit_dict)]
    total_events = sum(a.get("n_events", len(a.get("events", []))) for _, a in logs)
    all_verified = all(a.get("verified", False) for _, a in logs if a)

    summary_rows = [[scope, a.get("n_events", len(a.get("events", []))),
                     a.get("verified"), (a.get("head") or "")[:8]] for scope, a in logs]

    # flattened, ordered event history across all logs (event-history view)
    event_rows = []
    for scope, a in logs:
        for e in a.get("events", []):
            event_rows.append([scope, e.get("seq"), e.get("kind"),
                               (e.get("event_hash", "") or "")[:8]])

    # version history = the version_changed events across all logs
    version_records = []
    for _, a in logs:
        version_records.extend(a.get("events", []))

    sections = [
        kv_panel("Unified Audit Summary", {
            "n_logs": len(logs), "total_events": total_events, "all_verified": all_verified,
        }),
        badges("Audit Integrity (per subsystem)",
               [(scope, a.get("verified", False)) for scope, a in logs]),
        table("Audit Logs", ["scope", "events", "verified", "head"], summary_rows),
        table("Event History (all subsystems)", ["scope", "seq", "event", "hash"],
              event_rows[:200]),
    ]
    viz = [audit_timeline(version_records, title="All Audit Events (ordered)"),
           version_history(version_records)]
    return [Page("audit", "Audit", sections, viz)]
