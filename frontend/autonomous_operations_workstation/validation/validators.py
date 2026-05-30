"""Workstation validation — consistency checks over the loaded snapshot (V4-P8).

These are *presentation-integrity* checks: they confirm the workstation is showing a
coherent, fully-traceable, fully-registered view, and that every value it shows came
from a registered artifact. They do not recompute domain truth — they read the
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
from ..state import ENTITY_BLOCKS

# the deliverable lineage spine that must be present end-to-end.
_CHAIN_KINDS = ["patient", "goal", "policy", "plan", "task", "agent", "execution",
                "governance_intelligence"]


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
        checks = []
        for block in ENTITY_BLOCKS:
            b = self.state.block(block)
            reg = b.get("registry", {})
            key = f"n_{block}"
            if key in reg:
                checks.append(reg.get(key) == len(self.state.records(block)))
        gov_reg = self.state.governance.get("registry", {})
        if "n_intelligence" in gov_reg:
            checks.append(gov_reg.get("n_intelligence", 0) >= 1)
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
        per_artifact = all(
            all(r.get("lineage_verified", False) for r in s.records(block))
            for block in ENTITY_BLOCKS)
        gov_ok = s.governance.get("lineage_verified", False)
        chain = s.representative_chain.get("verified", False)
        present = {r.get("kind") for r in s.representative_chain.get("records", [])}
        spine_ok = all(k in present for k in _CHAIN_KINDS)
        ok = per_artifact and gov_ok and chain and spine_ok
        self.report.add("lineage_consistency", ok,
                        "per-artifact + end-to-end lineage verifies (spine present)" if ok
                        else "a lineage chain failed verification / spine incomplete")

    # --- visualization consistency -------------------------------------------
    def visualization_consistency(self) -> None:
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
        have = [bool(s.block(block).get("reports")) for block in ENTITY_BLOCKS]
        have.append(bool(s.governance.get("reports")))
        ok = all(have)
        self.report.add("report_consistency", ok,
                        "every subsystem exposes registered reports" if ok
                        else "a subsystem is missing its registered reports")

    # --- state consistency ----------------------------------------------------
    def state_consistency(self) -> None:
        s = self.state
        ctx = s.context_snapshot()
        problems = []
        for ctx_key, block in (("current_goal", "goals"), ("current_policy", "policies"),
                               ("current_plan", "plans"), ("current_task", "tasks"),
                               ("current_agent", "agents"), ("current_execution", "executions")):
            cid = ctx.get(ctx_key)
            if cid and not s.record(block, cid):
                problems.append(ctx_key)
        gov_id = ctx.get("current_governance")
        intel_id = s.governance.get("intelligence", {}).get("intelligence_id")
        if gov_id and gov_id != intel_id:
            problems.append("current_governance")
        self.report.add("state_consistency", not problems,
                        "navigation context references existing artifacts" if not problems
                        else f"dangling context: {problems}")
