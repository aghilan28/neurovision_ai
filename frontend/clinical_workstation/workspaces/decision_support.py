"""Decision Support workspace — render registered V2-P6 decision artifacts.

Decision support only: this view presents context, evidence, risk, prioritization,
and guidance. It surfaces the explicit "clinician remains the decision-maker"
framing carried on every decision-support record; it never presents a diagnosis,
treatment, medication, or clinical order (those are out of scope by construction).
"""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges, validation_badges
from ..visualizations import decision_context


def decision_pages(state) -> list:
    ds = state.decision_support
    if not ds:
        return [Page("decision", "Decision Support",
                     [kv_panel("Decision Support", {"available": False})], [])]
    pages = [_overview(state, ds)]
    for bundle in ds.get("bundles", []):
        pages.append(_bundle_detail(bundle))
    return pages


def _overview(state, ds: dict) -> Page:
    rows = []
    for b in ds.get("bundles", []):
        arts = b.get("artifacts", {})
        risk = arts.get("risk_context", {}).get("artifact", {})
        prio = arts.get("prioritization", {}).get("artifact", {})
        rows.append([b.get("case_id", "")[:14], b.get("record_id", "")[:18],
                     risk.get("band"), risk.get("aggregate"),
                     prio.get("level"), prio.get("score")])
    sections = [
        kv_panel("Decision Registry", {
            "n_artifacts": ds.get("registry", {}).get("n_artifacts"),
            "registry_version": ds.get("registry", {}).get("decision_registry_version"),
            "scope": "decision support only — clinician remains the decision-maker",
        }),
        table("Decision Support Records",
              ["case", "record", "risk_band", "risk_agg", "priority", "score"], rows),
        badges("Decision Audit", [("audit_verified", ds.get("audit", {}).get("verified", False))]),
    ]
    return Page("decision-overview", "Decision Support — Overview", sections, [])


def _bundle_detail(bundle: dict) -> Page:
    arts = bundle.get("artifacts", {})
    context = arts.get("decision_context", {}).get("artifact", {})
    evidence = arts.get("evidence_bundle", {}).get("artifact", {})
    risk = arts.get("risk_context", {}).get("artifact", {})
    prio = arts.get("prioritization", {}).get("artifact", {})
    guidance = arts.get("guidance", {}).get("artifact", {})
    record = arts.get("decision_support", {}).get("artifact", {})
    case_id = bundle.get("case_id", "")

    evidence_rows = [[i.get("evidence_id", "")[:18], i.get("evidence_type") or i.get("type"),
                      i.get("confidence"), i.get("rank")]
                     for i in evidence.get("items", evidence.get("evidence", []))]
    risk_rows = [[c.get("name"), c.get("value"), (c.get("basis") or "")[:54]]
                 for c in risk.get("components", [])]
    factor_rows = [[f.get("name"), f.get("contribution"), (f.get("detail") or "")[:40]]
                   for f in prio.get("factors", [])]
    guidance_rows = [[g.get("category"), (g.get("message") or "")[:70]]
                     for g in guidance.get("items", [])]

    sections = [
        kv_panel("Decision Context", {
            "context_id": context.get("context_id"), "case_id": context.get("case_id"),
            "patient_id": context.get("patient_id"),
            "counts": context.get("counts"), "completeness": context.get("completeness"),
        }),
        table("Evidence Bundle (all evidence; nothing hidden)",
              ["evidence", "type", "confidence", "rank"], evidence_rows),
        kv_panel("Risk Context", {"band": risk.get("band"), "aggregate": risk.get("aggregate")}),
        table("Risk Components", ["component", "value", "basis"], risk_rows),
        kv_panel("Prioritization", {"level": prio.get("level"), "score": prio.get("score"),
                                    "reason": prio.get("reason")}),
        table("Priority Factors", ["factor", "contribution", "detail"], factor_rows),
        table("Guidance (review/evidence/knowledge/investigation/risk only)",
              ["category", "message"], guidance_rows),
        kv_panel("Decision Support Record", {
            "record_id": record.get("record_id"),
            "explanation": record.get("explanation"),
        }),
        validation_badges("Guidance Validation (scope-checked)",
                          arts.get("guidance", {}).get("validation", {})),
        validation_badges("Decision Record Validation",
                          arts.get("decision_support", {}).get("validation", {})),
    ]
    viz = [decision_context(risk)]
    return Page(f"decision-{case_id}", f"Decision {case_id[:14]}", sections, viz)
