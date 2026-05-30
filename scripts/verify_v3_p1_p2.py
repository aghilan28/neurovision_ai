"""Final validation for V3-P1 + V3-P2.

Objectively verifies the directive's 20 final-validation criteria and prints a
PASS/FAIL line per criterion. Exits non-zero if any criterion fails.

    python -m scripts.verify_v3_p1_p2
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    from backend.operational_events import taxonomy, lifecycle, LogicalClock
    from backend.temporal_intelligence import TemporalIntelligenceService
    import sys as _sys
    _sys.path.insert(0, str(REPO / "tests"))
    from _v3_helpers import build_v3

    fx = build_v3(2)
    evs = fx.events
    case_id = next(iter(fx.cases))
    review_ids = [r.review_id for r in fx.reviews.values() if r.case_id == case_id]
    finding_ids = [f.finding_id for f in fx.findings.values() if f.case_id == case_id]
    sources = [case_id] + review_ids + finding_ids

    # --- V3-P1 events --------------------------------------------------------
    check("1. Event taxonomy works",
          "governance" in taxonomy.categories() and taxonomy.category_of("CASE_CREATED") == "case"
          and not taxonomy.is_valid("case", "REVIEW_COMPLETED"))
    check("2. Event registry works",
          all(evs.registry.exists(e.event_id) for e in fx.all_events)
          and len(evs.registry.list_events()) == len(fx.all_events))
    seq = evs.link_sequence([e.event_id for e in fx.all_events[:3]])
    check("3. Event relationships work",
          len(seq) == 2 and all(evs.registry.relationship(r.relationship_id) for r in seq))
    case_event = next(e for e in fx.all_events if e.category == "case")
    check("4. Event lineage works",
          fx.cs.lineage.verify_chain(case_event.lineage_id)
          and {"event", "case", "patient"} <= {r.kind for r in fx.cs.lineage.chain(case_event.lineage_id)})
    check("5. Event audit works", evs.audit.verify() and len(evs.audit) > 0)
    check("6. Event validation works", all(evs.validate(e).ok for e in fx.all_events))
    # immutability: supersession flips status without rewriting the fact
    target = fx.all_events[0]
    new = evs.record_event(event_type="CASE_UPDATED", source_entity_id=target.source_entity_id,
                           source_version="v-next", source_audit_event_hash="deadbeefdeadbeef",
                           clock=LogicalClock(99, 0, "1970-01-01T00:00:00Z"), source_kind="case",
                           supersedes=target.event_id,
                           parents=(evs.registry.get(target.event_id).lineage_id,))
    check("7. Event immutability works",
          evs.registry.get(target.event_id).status == lifecycle.SUPERSEDED
          and new.supersedes == target.event_id
          and not lifecycle.can_transition("superseded", "active"))

    # --- V3-P2 temporal ------------------------------------------------------
    ti = TemporalIntelligenceService(evs).load_events(fx.all_events)
    timeline = ti.build_timeline(subject_kind="case", subject_id=case_id, source_entity_ids=sources)
    op_timeline = ti.build_operational_timeline()
    history = ti.build_history(subject_kind="case", subject_id=case_id, source_entity_ids=sources)
    evolution = ti.build_evolution(subject_kind="case", subject_id=case_id, source_entity_ids=[case_id])
    analytics = ti.build_analytics(scope="operational")

    check("8. Timeline engine works", timeline.length > 0
          and op_timeline.length == len(fx.all_events))
    check("9. History reconstruction works", history.length > 0
          and all(e.source_version for e in history.entries))
    check("10. State evolution works",
          evolution.n_transitions > 0 and evolution.steps[0].from_state is None
          and all(c.from_state == p.to_state for p, c in zip(evolution.steps, evolution.steps[1:])))
    am = analytics.metric("operational_event_total")
    check("11. Temporal analytics works",
          am is not None and am.steps == len(fx.all_events)
          and analytics.metric("case_lifecycle_steps").observed)
    check("12. Temporal registry works",
          ti.registry.exists(timeline.timeline_id) and ti.registry.exists(analytics.analytics_id))
    check("13. Temporal lineage works",
          fx.cs.lineage.verify_chain(timeline.lineage_id)
          and {"timeline", "event", "case", "patient"} <= {r.kind for r in fx.cs.lineage.chain(timeline.lineage_id)})
    check("14. Temporal validation works",
          all(ti.validate(a, k).ok for a, k in [(timeline, "timeline"), (history, "history"),
                                                (evolution, "evolution"), (analytics, "temporal_analytics")]))
    contracts = ti.visualization_contracts(timeline=timeline, evolution=evolution, analytics=analytics)
    check("15. Visualization contracts exist",
          {c["contract_type"] for c in contracts} ==
          {"timeline", "event_sequence", "evolution_graph", "duration_graph",
           "trend_graph", "operational_dashboard"})

    # --- gates / lineage / boundaries ----------------------------------------
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q",
                           "tests/test_operational_events.py", "tests/test_temporal_intelligence.py",
                           "tests/test_v3_p1_p2_e2e.py", "tests/test_boundaries.py"],
                          cwd=str(REPO), capture_output=True, text=True)
    last = (proc.stdout.strip().splitlines() or [""])[-1]
    check("16. All tests pass", proc.returncode == 0, last)

    # governance gates: every event + temporal artifact passed its gate (they are
    # registered, which only happens after the gate). Re-affirm with a fresh fixture
    # (criterion 7 above intentionally superseded an event, mutating its status).
    fresh = build_v3(2)
    fresh_ti = TemporalIntelligenceService(fresh.events).load_events(fresh.all_events)
    ftl = fresh_ti.build_operational_timeline()
    fan = fresh_ti.build_analytics(scope="operational")
    check("17. Governance gates pass",
          all(fresh.events.validate(e).ok for e in fresh.all_events)
          and fresh_ti.validate(ftl, "timeline").ok
          and fresh_ti.validate(fan, "temporal_analytics").ok)

    bnd = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_boundaries.py"],
                         cwd=str(REPO), capture_output=True, text=True)
    check("18. Quality gates pass", bnd.returncode == 0,
          (bnd.stdout.strip().splitlines() or [""])[-1])

    # V2 lineage intact: the case/finding chains still verify after V3 processing.
    v2_ok = (fx.cs.lineage.verify_chain(fx.cases[case_id].lineage_id)
             and all(fx.cs.lineage.verify_chain(fx.findings[fid].lineage_id) for fid in finding_ids))
    check("19. Version 2 lineage remains intact", v2_ok)

    check("20. No architectural boundary violations exist", bnd.returncode == 0)

    print("\nV3-P1 + V3-P2 FINAL VALIDATION")
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
