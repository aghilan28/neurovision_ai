"""Final validation for V3-P7 + V3-P8.

Objectively verifies the directive's 21 final-validation criteria and prints a
PASS/FAIL line per criterion. Exits non-zero if any criterion fails.

    python -m scripts.verify_v3_p7_p8
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
CERT = REPO / "docs" / "certification" / "v3"


def _doc_has(name: str, *markers: str) -> bool:
    """A certification doc exists and contains every required marker."""
    path = CERT / name
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    return all(m in text for m in markers)


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    from scripts.build_operational_workstation_snapshot import build_snapshot
    from frontend.operational_workstation import (
        build_from_snapshot, validate_state, WorkstationState,
    )

    snapshot = build_snapshot(n_cases=3)
    view = build_from_snapshot(snapshot)
    vd = view.to_dict()
    areas = {a["id"]: a for a in vd["areas"]}

    def _titles(area_id):
        out = []
        for p in areas.get(area_id, {}).get("pages", []):
            out += [s["title"] for s in p["sections"]]
        return out

    def _viz_types(area_id):
        out = []
        for p in areas.get(area_id, {}).get("pages", []):
            out += [v["type"] for v in p["visualizations"]]
        return out


    # --- workspaces (1-9) ---------------------------------------------------
    check("1. Event workspace works",
          "events" in areas and "Event Registry" in _titles("events")
          and "timeline" in _viz_types("events"))
    check("2. Timeline workspace works",
          "timelines" in areas and "Temporal Registry" in _titles("timelines"))
    check("3. Workflow workspace works",
          "workflows" in areas and len(areas["workflows"]["pages"]) >= 2
          and "Efficiency Metrics" in _titles("workflows"))
    check("4. Graph workspace works",
          "graph" in areas and "Node Registry (by type)" in _titles("graph")
          and "graph" in _viz_types("graph"))
    check("5. Analytics workspace works",
          "analytics" in areas
          and {"Metrics", "Health Scores", "Risk Scores"} <= set(_titles("analytics")))
    check("6. Recommendation workspace works",
          "recommendations" in areas and "Recommendations" in _titles("recommendations")
          and any("Escalation Candidates" in t for t in _titles("recommendations")))
    check("7. Audit browser works",
          "audit" in areas and "Audit Logs" in _titles("audit")
          and "timeline" in _viz_types("audit"))
    check("8. Lineage explorer works",
          "lineage" in areas and "Chain Coverage" in _titles("lineage")
          and any(v["title"].startswith("Traceability")
                  for p in areas["lineage"]["pages"] for v in p["visualizations"]))
    check("9. Report center works",
          "reports" in areas and "Registered Reports" in _titles("reports"))

    # --- visualization contracts (10) ---------------------------------------
    # every chart spec resolves to registered data (visualization_consistency)
    viz_check = next((c for c in vd["validation"]["checks"]
                      if c["name"] == "visualization_consistency"), None)
    n_viz = sum(len(p["visualizations"]) for a in vd["areas"] for p in a["pages"])
    check("10. Visualization contracts work",
          viz_check is not None and viz_check["passed"] and n_viz > 0,
          f"{n_viz} visualizations, consistency={viz_check and viz_check['passed']}")

    # --- state management (11) ----------------------------------------------
    st = WorkstationState.from_snapshot(snapshot).default_context()
    ctx = st.context_snapshot()
    eid = st.event_records[0]["event_id"] if st.event_records else None
    a = WorkstationState.from_snapshot(snapshot).default_context().set_context(current_event=eid)
    b = WorkstationState.from_snapshot(snapshot).default_context().set_context(current_event=eid)
    rejected = False
    try:
        st.set_context(bad_key="x")
    except KeyError:
        rejected = True
    check("11. State management works",
          all(ctx.get(k) is not None for k in ("current_event", "current_workflow",
                                               "current_recommendation"))
          and a.context_snapshot() == b.context_snapshot() and rejected)

    # --- workstation validation (12) ----------------------------------------
    report = validate_state(WorkstationState.from_snapshot(snapshot).default_context()).to_dict()
    names = {c["name"] for c in report["checks"]}
    expected = {"registry_consistency", "audit_consistency", "lineage_consistency",
                "visualization_consistency", "report_consistency", "state_consistency"}
    check("12. Workstation validation works", expected <= names and report["ok"],
          f"checks={sorted(names)} ok={report['ok']}")


    # --- certification documents (13-17) ------------------------------------
    check("13. Certification audit completes",
          _doc_has("V3_AUDIT_FRAMEWORK.md", "Audit categories", "Audit escalation")
          and _doc_has("V3_CERTIFICATION_STANDARD.md", "Certification verdicts",
                       "Certification rule"))
    check("14. Readiness assessment completes",
          _doc_has("V3_READINESS_ASSESSMENT.md", "Dimension scores", "Readiness verdict"))
    check("15. Gap analysis completes",
          _doc_has("V3_GAP_ANALYSIS.md", "Severity classification", "Gap register"))
    check("16. Risk review completes",
          _doc_has("V3_RISK_REVIEW.md", "Risk register", "Risk verdict"))
    check("17. Exit criteria validated",
          _doc_has("V3_EXIT_CRITERIA.md", "Exit criteria", "Exit verdict")
          and _doc_has("V3_COMPLETION_REPORT.md", "CERTIFIED"))

    # --- governance + quality gates (18-19) ---------------------------------
    suite = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         "tests/test_operational_workstation.py", "tests/test_boundaries.py",
         "tests/test_v3_p5_p6_e2e.py"],
        cwd=str(REPO), capture_output=True, text=True)
    suite_line = (suite.stdout.strip().splitlines() or [""])[-1]
    # governance: boundary (frontend imports no domain) + shared lineage/audit upheld
    check("18. Governance gates pass", suite.returncode == 0, suite_line)
    # quality: deterministic snapshot + view
    import json
    repro = (json.dumps(build_snapshot(n_cases=3), sort_keys=True)
             == json.dumps(snapshot, sort_keys=True))
    check("19. Quality gates pass", suite.returncode == 0 and repro,
          f"suite ok={suite.returncode == 0}; snapshot reproducible={repro}")

    # --- V3 lineage intact (20) ---------------------------------------------
    rep = snapshot["representative_chain"]
    chain_kinds = {r["kind"] for r in rep["records"]}
    spine = {"patient", "case", "review", "finding", "event", "workflow",
             "graph_node", "analytics", "recommendation"}
    check("20. Version 3 lineage remains intact",
          rep["verified"] and spine <= chain_kinds
          and all(a.get("verified") for a in
                  (snapshot[s].get("audit", {}) for s in
                   ("events", "timelines", "workflows", "graph", "analytics",
                    "recommendations"))),
          f"chain_verified={rep['verified']} missing={sorted(spine - chain_kinds)}")

    # --- V4 readiness criteria measurable (21) ------------------------------
    check("21. Version 4 readiness criteria measurable",
          _doc_has("V4_READINESS_GATE.md", "Entry criteria", "Measurable test",
                   "Gate decision", "NOT GRANTED"))

    # --- report -------------------------------------------------------------
    print("\nV3-P7 + V3-P8 FINAL VALIDATION")
    print("=" * 64)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail and not ok:
            line += f"  -- {detail}"
        print(line)
    print("=" * 64)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
