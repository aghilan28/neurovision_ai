"""Audit workspace — a unified browser over every immutable audit log."""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges
from ..visualizations import audit_timeline, version_history


def _all_logs(state) -> list:
    """Collect (scope, id, audit_dict) for every audit log in the snapshot."""
    logs = []
    for c in state.cases:
        logs.append(("case", c.get("case_id"), c.get("audit", {})))
    for r in state.reviews:
        logs.append(("review", r.get("review_id"), r.get("audit", {})))
    for f in state.findings:
        logs.append(("finding", f.get("finding_id"), f.get("audit", {})))
    if state.knowledge:
        logs.append(("knowledge", "knowledge", state.knowledge.get("audit", {})))
    if state.intelligence:
        logs.append(("intelligence", "intelligence", state.intelligence.get("audit", {})))
    if state.decision_support:
        logs.append(("decision", "decision", state.decision_support.get("audit", {})))
    return logs


def audit_pages(state) -> list:
    logs = _all_logs(state)
    total_events = sum(a.get("n_events", 0) for _, _, a in logs)
    all_verified = all(a.get("verified", False) for _, _, a in logs if a)

    summary_rows = [[scope, (aid or "")[:18], a.get("n_events"), a.get("verified"),
                     (a.get("head") or "")[:8]] for scope, aid, a in logs]

    # A flattened, ordered event history across all logs (event-history view).
    event_rows = []
    for scope, aid, a in logs:
        for e in a.get("events", []):
            event_rows.append([scope, (aid or "")[:12], e.get("seq"), e.get("kind"),
                               e.get("event_hash", "")[:8]])

    # Version history = the version_changed events across all logs.
    version_records = []
    for _, _, a in logs:
        version_records.extend(a.get("events", []))

    sections = [
        kv_panel("Unified Audit Summary", {
            "n_logs": len(logs), "total_events": total_events, "all_verified": all_verified,
        }),
        badges("Audit Integrity (per scope)",
               [(f"{scope}", a.get("verified", False)) for scope, _, a in logs]),
        table("Audit Logs", ["scope", "id", "events", "verified", "head"], summary_rows),
        table("Event History (all scopes)", ["scope", "id", "seq", "event", "hash"],
              event_rows),
    ]
    viz = [audit_timeline(version_records, title="All Audit Events (ordered)"),
           version_history(version_records)]
    return [Page("audit", "Audit", sections, viz)]
