"""Recommendation workspace — guidance, priorities, optimization, escalation.

Surfaces explainable operational recommendations: every item shows its priority,
its cited evidence, and the analytics it links to. Recommendations are operational
**suggestions** only — never clinical, never executed, never auto-escalated; the
workspace presents that framing explicitly.
"""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges, text
from ..visualizations import recommendation_priorities


def recommendation_pages(state) -> list:
    block = state.recommendations
    registry = block.get("registry", {})
    recs = state.recommendation_records
    by_kind = block.get("by_kind", {})
    audit = block.get("audit", {})

    rows = [[r.get("kind"), r.get("priority", {}).get("level"),
             round(float(r.get("priority", {}).get("score", 0.0)), 3),
             len(r.get("evidence", [])), r.get("statement", "")[:60],
             r.get("lineage_verified")]
            for r in recs]

    # escalation candidates are surfaced explicitly (no automatic escalation)
    escalations = [r for r in recs if r.get("kind") == "escalation"]
    esc_rows = [[r.get("priority", {}).get("level"),
                 r.get("priority", {}).get("reason", "")[:50],
                 len(r.get("evidence", []))]
                for r in escalations]

    sections = [
        kv_panel("Recommendation Registry", {
            "n_recommendations": block.get("n_recommendations"),
            "recommendation_registry_version": registry.get("recommendation_registry_version"),
            "audit_verified": audit.get("verified"),
            "guidance": len(by_kind.get("guidance", [])),
            "optimization": len(by_kind.get("optimization", [])),
            "escalation": len(by_kind.get("escalation", [])),
        }),
        text("Scope", "Operational suggestions only — not clinical decision support, "
                      "diagnosis, or treatment. No recommendation is executed or auto-escalated."),
        badges("Recommendation Validation",
               [(r.get("kind") + ":" + (r.get("recommendation_id") or "")[:8],
                 r.get("validation", {}).get("ok", False)) for r in recs]),
        table("Recommendations", ["kind", "priority", "score", "evidence", "statement",
                                  "lineage_ok"], rows),
        table("Escalation Candidates (human review required)",
              ["priority", "reason", "evidence"], esc_rows),
    ]
    viz = [recommendation_priorities(recs)]
    return [Page("recommendations", "Recommendations", sections, viz)]
