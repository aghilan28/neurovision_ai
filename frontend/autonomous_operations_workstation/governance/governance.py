"""Governance workspace (V4-P8).

Presents the V4-P7 Governance Intelligence Layer: approval analytics, violation
analytics, escalation analytics, risk analytics, governance health, and the
governance reports. Pure presentation — every value comes from the governance
intelligence the backend already recorded into the snapshot.
"""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges, bar_chart


def _report(state, key: str) -> dict:
    return state.governance.get("reports", {}).get(key, {})


def governance_pages(state) -> list:
    gov = state.governance
    intel = gov.get("intelligence", {})
    approvals = state.approvals()
    violations = state.violations()
    escalations = state.escalations()
    risks = state.risks()
    metrics = state.metrics()

    approval_metrics = _report(state, "approval_report").get("metrics", {})
    violation_summary = _report(state, "violation_report").get("summary", {})
    escalation_summary = _report(state, "escalation_report").get("summary", {})
    risk_summary = _report(state, "governance_risk_report").get("summary", {})

    # --- governance health page ---------------------------------------------
    health = kv_panel("Governance Health", {
        "intelligence_id": intel.get("intelligence_id"),
        "scope": intel.get("scope"),
        "n_observed": intel.get("n_observed"),
        "health_score": intel.get("health_score"),
        "n_approvals": len(approvals), "n_violations": len(violations),
        "n_escalations": len(escalations), "n_risks": len(risks),
        "audit_verified": gov.get("audit", {}).get("verified", False),
        "lineage_verified": gov.get("lineage_verified", False),
    })
    metric_rows = [[m.get("name"), m.get("value"), m.get("unit"), m.get("detail")]
                   for m in metrics]
    health_page = Page("governance-health", "Governance Health",
                       [health, table("Governance Metrics",
                                       ["metric", "value", "unit", "detail"], metric_rows)],
                       [bar_chart("Risk by Dimension (mean)",
                                  list(risk_summary.get("by_dimension_mean", {}).keys()),
                                  list(risk_summary.get("by_dimension_mean", {}).values()))])

    # --- approval analytics page --------------------------------------------
    approval_rows = [[(a.get("entity_id", "") or "")[:18], a.get("entity_kind"),
                      a.get("approval_state"), a.get("latency_steps"), a.get("approved")]
                     for a in approvals]
    approval_page = Page("governance-approvals", "Approval Analytics", [
        kv_panel("Approval Analytics", approval_metrics),
        table("Approvals", ["entity", "kind", "state", "latency", "approved"], approval_rows),
    ])

    # --- violation analytics page -------------------------------------------
    violation_rows = [[(v.get("entity_id", "") or "")[:18], v.get("entity_kind"),
                       v.get("violation_type"), v.get("severity"), v.get("impact")]
                      for v in violations]
    violation_page = Page("governance-violations", "Violation Analytics", [
        kv_panel("Violation Analytics", violation_summary),
        badges("Clean (no high/critical violations)",
               [("violations", violation_summary.get("n_high_or_critical", 0) == 0)]),
        table("Violations", ["entity", "kind", "type", "severity", "impact"], violation_rows),
    ])

    # --- escalation analytics page ------------------------------------------
    escalation_rows = [[(e.get("entity_id", "") or "")[:18], e.get("entity_kind"),
                        e.get("outcome"), e.get("delay_steps"), e.get("effective")]
                       for e in escalations]
    escalation_page = Page("governance-escalations", "Escalation Analytics", [
        kv_panel("Escalation Analytics", escalation_summary),
        table("Escalations", ["entity", "kind", "outcome", "delay", "effective"],
              escalation_rows),
    ])

    # --- risk analytics page ------------------------------------------------
    highest = _report(state, "governance_risk_report").get("highest_risks", [])
    risk_rows = [[(r.get("entity_id", "") or "")[:18], r.get("dimension"), r.get("level"),
                  r.get("score"), r.get("explanation")] for r in highest]
    risk_page = Page("governance-risk", "Risk Analytics", [
        kv_panel("Risk Analytics", risk_summary),
        table("Highest Risks", ["entity", "dimension", "level", "score", "explanation"],
              risk_rows),
    ], [bar_chart("Risk by Level",
                  list(risk_summary.get("by_level", {}).keys()),
                  list(risk_summary.get("by_level", {}).values()))])

    return [health_page, approval_page, violation_page, escalation_page, risk_page]
