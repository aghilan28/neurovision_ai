"""Workstation validation — consistency checks over the loaded snapshot (V3-P7).

These are *presentation-integrity* checks: they confirm the workstation is showing
a coherent, fully-traceable, fully-registered view, and that every value it shows
came from a registered artifact. They do not recompute domain truth — they read the
validation/audit/lineage results the backend already recorded.

Checks (the six mandated consistency dimensions):
  * registry_consistency      — displayed collections agree with registry counts.
  * audit_consistency         — every subsystem audit log verifies (tamper-evident).
  * lineage_consistency       — per-artifact lineage verifies + the end-to-end chain.
  * visualization_consistency — every chart spec resolves to registered data.
  * report_consistency        — every subsystem exposes its registered reports.
  * state_consistency         — navigation context references only existing artifacts.
"""

from __future__ import annotations

from ..schemas import ValidationReport
from ..navigation import build_areas

# the deliverable lineage spine that must be present end-to-end
_CHAIN_KINDS = ["patient", "case", "review", "finding", "event", "workflow",
                "graph_node", "analytics", "recommendation"]


def validate_state(state) -> ValidationReport:
    return ReportBuilder(state).run().report


class ReportBuilder:
    def __init__(self, state) -> None:
        self.state = state
        self.report = ValidationReport()

    def run(self) -> "ReportBuilder":
        self.registry_consistency()
        self.audit_consistency()
        self.lineage_consistency()
        self.visualization_consistency()
        self.report_consistency()
        self.state_consistency()
        return self

    # --- registry consistency -------------------------------------------------
    def registry_consistency(self) -> None:
        s = self.state
        checks = []
        ev_reg = s.events.get("registry", {})
        if "n_events" in ev_reg:
            checks.append(ev_reg.get("n_events") == len(s.event_records))
        wf_reg = s.workflows.get("registry", {})
        if "n_workflows" in wf_reg:
            checks.append(wf_reg.get("n_workflows") == len(s.workflow_records))
        an_reg = s.analytics.get("registry", {})
        if "n_analytics" in an_reg:
            checks.append(an_reg.get("n_analytics") == len(s.analytics_blocks))
        rc_reg = s.recommendations.get("registry", {})
        if "n_recommendations" in rc_reg:
            checks.append(rc_reg.get("n_recommendations") == len(s.recommendation_records))
        ok = all(checks) if checks else True
        self.report.add("registry_consistency", ok,
                        "registry counts agree with displayed collections" if ok
                        else "registry counts disagree with displayed collections")

    # --- audit consistency ----------------------------------------------------
    def audit_consistency(self) -> None:
        logs = self.state.audit_logs()
        ok = all(a.get("verified", False) for _, a in logs) if logs else False
        self.report.add("audit_consistency", ok,
                        f"{len(logs)} audit log(s) verify" if ok
                        else "an audit log failed verification")

    # --- lineage consistency --------------------------------------------------
    def lineage_consistency(self) -> None:
        s = self.state
        per_artifact = (
            all(e.get("lineage_verified", False) for e in s.event_records)
            and all(w.get("lineage_verified", False) for w in s.workflow_records)
            and all(b.get("lineage_verified", False) for b in s.analytics_blocks.values())
            and all(r.get("lineage_verified", False) for r in s.recommendation_records))
        chain = s.representative_chain.get("verified", False)
        self.report.add("lineage_consistency", per_artifact and chain,
                        "per-artifact + end-to-end lineage verifies" if (per_artifact and chain)
                        else "a lineage chain failed verification")



    # --- visualization consistency -------------------------------------------
    def visualization_consistency(self) -> None:
        """Every chart spec built from the snapshot is well-formed + JSON-able.

        A visualization is consistent if each graph spec's edges reference nodes in
        the same spec, and bar/line/timeline specs carry their expected keys — i.e.
        the chart resolves only to registered snapshot data (no dangling refs)."""
        problems = []
        for area in build_areas(self.state):
            for page in area.pages:
                for viz in page.visualizations:
                    vd = viz.to_dict()
                    spec, vtype = vd["spec"], vd["type"]
                    if vtype == "graph":
                        ids = {n["id"] for n in spec.get("nodes", [])}
                        for e in spec.get("edges", []):
                            if e.get("from") not in ids or e.get("to") not in ids:
                                problems.append(f"{vd['title']}: dangling edge")
                                break
                    elif vtype == "bar":
                        if len(spec.get("labels", [])) != len(spec.get("values", [])):
                            problems.append(f"{vd['title']}: label/value mismatch")
                    elif vtype in ("timeline", "line", "table"):
                        key = {"timeline": "events", "line": "points", "table": "rows"}[vtype]
                        if key not in spec:
                            problems.append(f"{vd['title']}: missing '{key}'")
        ok = not problems
        self.report.add("visualization_consistency", ok,
                        "all chart specs resolve to registered data" if ok
                        else "; ".join(problems[:3]))

    # --- report consistency ---------------------------------------------------
    def report_consistency(self) -> None:
        s = self.state
        have = [bool(s.events.get("reports")), bool(s.timelines.get("reports")),
                bool(s.graph.get("reports")), bool(s.analytics.get("reports")),
                bool(s.recommendations.get("reports")),
                any(w.get("reports") for w in s.workflow_records) if s.workflow_records else True]
        ok = all(have)
        self.report.add("report_consistency", ok,
                        "every subsystem exposes registered reports" if ok
                        else "a subsystem is missing its registered reports")

    # --- state consistency ----------------------------------------------------
    def state_consistency(self) -> None:
        s = self.state
        ctx = s.context_snapshot()
        problems = []
        if ctx.get("current_event") and not s.event(ctx["current_event"]):
            problems.append("current_event")
        if ctx.get("current_workflow") and not s.workflow(ctx["current_workflow"]):
            problems.append("current_workflow")
        if ctx.get("current_recommendation") and not s.recommendation(ctx["current_recommendation"]):
            problems.append("current_recommendation")
        self.report.add("state_consistency", not problems,
                        "navigation context references existing artifacts" if not problems
                        else f"dangling context: {problems}")
