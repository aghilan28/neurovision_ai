"""Final validation for V3-P3 + V3-P4.

Objectively verifies the directive's 21 final-validation criteria and prints a
PASS/FAIL line per criterion. Exits non-zero if any criterion fails.

    python -m scripts.verify_v3_p3_p4
"""

from __future__ import annotations

import _repo_bootstrap  # noqa: F401

import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sys.path.insert(0, str(REPO / "tests"))
    from _v3b_helpers import build_v3b
    from backend.operational_graph import NodeType, EdgeType
    from backend.operational_graph.ontology import edge_allowed

    fx = build_v3b(2)
    wi = fx.workflows
    g = fx.graph
    tracker = fx.base.cs.lineage
    case_id = next(iter(fx.base.cases))

    def case_workflow():
        for wf in fx.workflow_records.values():
            if wf.subject_id == case_id and wf.workflow_type == "case_workflow":
                return wf
        return None

    wf = case_workflow()

    # --- V3-P3 workflow ------------------------------------------------------
    check("1. Workflow registry works",
          all(wi.registry.exists(w) for w in fx.workflow_records)
          and len(wi.registry.list_workflows()) == len(fx.workflow_records))
    check("2. Transition engine works",
          wf.n_transitions > 0 and wf.transitions[0].to_state == "created"
          and all(c.from_state == p.to_state for p, c in zip(wf.transitions, wf.transitions[1:])))
    check("3. Dependency engine works",
          len(wf.dependencies) > 0
          and {d.relation for d in wf.dependencies} <= {"upstream", "downstream", "blocked",
                                                         "waiting", "completed"})
    check("4. Bottleneck analysis works",
          any(m.name == "workflow_stall" for m in wf.metrics)
          and any(m.name == "rework_states" for m in wf.metrics))
    check("5. Efficiency analytics works",
          wf.metric("completion_rate") is not None
          and 0.0 <= wf.metric("workflow_health_score").value <= 1.0)
    check("6. Workflow lineage works",
          tracker.verify_chain(wf.lineage_id)
          and {"workflow", "event", "case", "patient"} <= {r.kind for r in tracker.chain(wf.lineage_id)})
    check("7. Workflow validation works",
          all(wi.validate(w).ok for w in fx.workflow_records.values()))

    # --- V3-P4 graph ---------------------------------------------------------
    nodes = g.registry.list_nodes()
    edges = g.registry.list_edges()
    check("8. Graph node system works",
          len(nodes) > 0 and all(g.registry.node(n).source_id for n in nodes))
    check("9. Graph edge system works",
          len(edges) > 0 and all(
              edge_allowed(g.registry.edge(e).edge_type, g.registry.edge(e).source_type,
                           g.registry.edge(e).target_type) for e in edges))
    check("10. Relationship engine works",
          not edge_allowed(EdgeType.OWNS, NodeType.CASE, NodeType.PATIENT)
          and edge_allowed(EdgeType.OWNS, NodeType.PATIENT, NodeType.CASE))
    check("11. Graph ontology works",
          "patient" in NodeType.PATIENT and len(g.reports()["relationship_report"]["ontology"]["node_types"]) >= 8)
    check("12. Graph registry works",
          all(g.registry.exists(n) for n in nodes) and all(g.registry.exists(e) for e in edges))
    case_node = g.registry.node_by_source(case_id)
    nb = g.queries.neighborhood(case_node.node_id, depth=2)
    check("13. Graph query layer works",
          case_node.node_id in nb["nodes"] and len(nb["nodes"]) >= 2
          and isinstance(g.queries.workflow_traversal(case_node.node_id), list))
    proj = g.build_projection(g.projections.by_node_types(
        "case", [NodeType.CASE, NodeType.REVIEW, NodeType.FINDING]))
    op_proj = g.build_projection(g.projections.operational())
    check("14. Graph projections work",
          proj.n_nodes >= 1 and op_proj.n_nodes == len(nodes) and g.validate(proj).ok)
    check("15. Graph lineage works",
          tracker.verify_chain(case_node.lineage_id)
          and {"graph_node", "case", "patient"} <= {r.kind for r in tracker.chain(case_node.lineage_id)})
    check("16. Graph validation works",
          all(g.validate(g.registry.node(n)).ok for n in nodes)
          and all(g.validate(g.registry.edge(e)).ok for e in edges))

    # --- suite / gates / lineage / boundaries --------------------------------
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q",
                           "tests/test_workflow_intelligence.py", "tests/test_operational_graph.py",
                           "tests/test_v3_p3_p4_e2e.py", "tests/test_boundaries.py"],
                          cwd=str(REPO), capture_output=True, text=True)
    check("17. All tests pass", proc.returncode == 0,
          (proc.stdout.strip().splitlines() or [""])[-1])

    # governance gates: re-affirm with a fresh fixture (gate runs before registry).
    fresh = build_v3b(2)
    gov_ok = (all(fresh.workflows.validate(w).ok for w in fresh.workflow_records.values())
              and all(fresh.graph.validate(fresh.graph.registry.node(n)).ok
                      for n in fresh.graph.registry.list_nodes()))
    check("18. Governance gates pass", gov_ok)

    # V2 lineage intact
    v2_ok = all(tracker.verify_chain(c.lineage_id) for c in fx.base.cases.values())
    check("19. Version 2 lineage remains intact", v2_ok)

    # V3 event/temporal lineage intact
    v3_ok = all(tracker.verify_chain(e.lineage_id) for e in fx.base.all_events)
    check("20. Version 3 event/temporal lineage remains intact", v3_ok)

    bnd = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_boundaries.py"],
                         cwd=str(REPO), capture_output=True, text=True)
    check("21. No architectural boundary violations exist", bnd.returncode == 0,
          (bnd.stdout.strip().splitlines() or [""])[-1])

    print("\nV3-P3 + V3-P4 FINAL VALIDATION")
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
