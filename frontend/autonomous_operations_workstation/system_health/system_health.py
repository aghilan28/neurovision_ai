"""System Health workspace (V4-P8) — the human-oversight landing area.

A single deterministic overview of the whole governed platform: entity counts,
audit integrity across every subsystem, end-to-end lineage health, the governance
health score, the monitoring flags (what needs human attention), and the governed
intervention controls available. Read-only.
"""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges
from ..controls import build_controls, controls_summary
from ..state import ENTITY_BLOCKS


def system_health_pages(state) -> list:
    meta = state.meta
    logs = state.audit_logs()
    all_audit_ok = all(a.get("verified", False) for _, a in logs) if logs else False

    counts = {f"n_{b}": len(state.records(b)) for b in ENTITY_BLOCKS}
    gov = state.governance
    intel = gov.get("intelligence", {})
    monitoring = state.monitoring()
    controls = build_controls(state)
    csummary = controls_summary(controls)

    lineage_ok = all(all(r.get("lineage_verified", False) for r in state.records(b))
                     for b in ENTITY_BLOCKS) and gov.get("lineage_verified", False) \
        and state.representative_chain.get("verified", False)

    overview = kv_panel("Platform Overview", {
        **counts,
        "patients": meta.get("patients", []),
        "governance_health": intel.get("health_score"),
        "all_audit_verified": all_audit_ok,
        "all_lineage_verified": lineage_ok,
        "end_to_end_chain_verified": state.representative_chain.get("verified", False),
    })
    oversight = kv_panel("Human Oversight", {
        "executions_requiring_intervention": monitoring.get(
            "n_executions_requiring_intervention", 0),
        "states_requiring_review": monitoring.get("n_states_requiring_review", 0),
        "monitoring_clear": monitoring.get("clear", True),
        "n_intervention_controls": csummary["n_controls"],
        "n_controls_enabled": csummary["n_enabled"],
        "all_controls_governed": csummary["all_governed"],
    })
    health_badges = badges("Subsystem Audit Integrity",
                           [(scope, a.get("verified", False)) for scope, a in logs])
    severity_rows = [["governance_health", intel.get("health_score")],
                     ["n_violations", len(state.violations())],
                     ["n_high_risks", sum(1 for r in state.risks()
                                          if r.get("level") in ("high", "critical"))],
                     ["n_escalations", len(state.escalations())]]
    sections = [overview, oversight, health_badges,
                table("Governance Indicators", ["indicator", "value"], severity_rows)]
    return [Page("system-health", "System Health", sections)]
