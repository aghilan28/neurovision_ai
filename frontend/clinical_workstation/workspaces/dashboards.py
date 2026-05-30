"""Dashboards / System Status — a cross-subsystem operational overview."""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges, metric_row


def _all_verified(items: list, getter) -> bool:
    return all(getter(it) for it in items) if items else True


def dashboard_pages(state) -> list:
    cases, reviews, findings = state.cases, state.reviews, state.findings
    intel, ds = state.intelligence, state.decision_support

    cases_valid = _all_verified(cases, lambda c: c.get("validation", {}).get("ok", False))
    reviews_valid = _all_verified(reviews, lambda r: r.get("validation", {}).get("ok", False))
    findings_valid = _all_verified(findings, lambda f: f.get("validation", {}).get("ok", False))
    audits_ok = (_all_verified(cases, lambda c: c.get("audit", {}).get("verified", False))
                 and _all_verified(reviews, lambda r: r.get("audit", {}).get("verified", False))
                 and _all_verified(findings, lambda f: f.get("audit", {}).get("verified", False)))
    lineage_ok = state.representative_chain.get("verified", False)

    subsystem_rows = [
        ["Clinical Cases (V2-P1)", len(cases), cases_valid],
        ["Clinical Review (V2-P2)", len(reviews), reviews_valid],
        ["Findings (V2-P3)", len(findings), findings_valid],
        ["Knowledge (V2-P4)", state.knowledge.get("concepts", {}).get("n_concepts"),
         state.knowledge.get("validation", {}).get("ok")],
        ["Intelligence (V2-P5)", intel.get("registry", {}).get("n_artifacts"),
         intel.get("analytics", {}).get("validation", {}).get("ok")],
        ["Decision Support (V2-P6)", ds.get("registry", {}).get("n_artifacts"),
         _all_verified(ds.get("bundles", []),
                       lambda b: b.get("artifacts", {}).get("decision_support", {})
                       .get("validation", {}).get("ok", False))],
    ]

    sections = [
        badges("System Status", [
            ("cases_valid", cases_valid), ("reviews_valid", reviews_valid),
            ("findings_valid", findings_valid), ("audit_verified", audits_ok),
            ("lineage_verified", lineage_ok),
        ]),
        metric_row("Workload", {
            "patients": len(state.meta.get("patients", [])),
            "cases": len(cases), "reviews": len(reviews), "findings": len(findings),
            "lineage_nodes": state.lineage.get("n_records"),
        }),
        table("Subsystems", ["subsystem", "artifacts", "valid"], subsystem_rows),
        kv_panel("Provenance", {
            "snapshot_version": state.snapshot.get("snapshot_version"),
            "source": state.snapshot.get("source"),
            "representative_chain_verified": lineage_ok,
        }),
    ]
    return [Page("dashboard", "System Status", sections, [])]
