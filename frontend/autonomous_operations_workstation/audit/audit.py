"""Audit workspace (V4-P8) — a unified browser over every V4 immutable audit log.

Goals, policies, plans, tasks, agents, executions, and governance intelligence audits
plus the flattened version/event history. Read-only; reflects the recorded
``verified`` flag each subsystem already computed.
"""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges, timeline


def audit_pages(state) -> list:
    logs = state.audit_logs()                 # list[(scope, audit_dict)]
    total_events = sum(a.get("n_events", len(a.get("events", []))) for _, a in logs)
    all_verified = all(a.get("verified", False) for _, a in logs if a)

    summary_rows = [[scope, a.get("n_events", len(a.get("events", []))),
                     a.get("verified"), (a.get("head") or "")[:8]] for scope, a in logs]

    # flattened, ordered event history across all logs
    event_rows = []
    version_records = []
    for scope, a in logs:
        for e in a.get("events", []):
            event_rows.append([scope, e.get("seq"), e.get("kind"),
                               (e.get("event_hash", "") or "")[:8]])
            version_records.append(e)

    sections = [
        kv_panel("Unified Audit Summary", {
            "n_logs": len(logs), "total_events": total_events, "all_verified": all_verified,
        }),
        badges("Audit Integrity (per subsystem)",
               [(scope, a.get("verified", False)) for scope, a in logs]),
        table("Audit Logs", ["scope", "events", "verified", "head"], summary_rows),
        table("Event / Version History (all subsystems)", ["scope", "seq", "event", "hash"],
              event_rows[:300]),
    ]
    viz = [timeline("All Audit Events (ordered)",
                    [{"seq": e.get("seq"), "kind": e.get("kind")} for e in version_records[:300]])]
    return [Page("audit", "Audit", sections, viz)]
