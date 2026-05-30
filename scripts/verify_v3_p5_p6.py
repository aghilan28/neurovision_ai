"""Final validation for V3-P5 + V3-P6.

Objectively verifies the directive's 22 final-validation criteria and prints a
PASS/FAIL line per criterion. Exits non-zero if any criterion fails.

    python -m scripts.verify_v3_p5_p6
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

    sys.path.insert(0, str(REPO / "tests"))
    from _v3c_helpers import build_v3c, all_recommendations
    from backend.operational_analytics import AnalyticsCategory, AnalyticsGovernanceGate
    from backend.operational_analytics import AnalyticsRecord, AnalyticsMetric
    from backend.operational_recommendations import (
        RecommendationKind, PriorityLevel, RecommendationGovernanceGate, level_for_score,
    )

    fx = build_v3c(2)
    oa = fx.analytics
    orr = fx.recommendations
    tracker = fx.base.base.cs.lineage
    A = fx.analytics_records
    recs = all_recommendations(fx)


    # --- V3-P5 analytics engines (1-6) --------------------------------------
    metrics = A[AnalyticsCategory.METRICS]
    check("1. Metrics engine works",
          metrics.metric("event_total").value > 0 and metrics.metric("workflow_total").value > 0
          and all(m.explanation for m in metrics.metrics))

    health = A[AnalyticsCategory.HEALTH]
    check("2. Health engine works",
          health.metric("operational_health") is not None
          and all(0.0 <= m.value <= 1.0 and m.explanation for m in health.metrics))

    perf = A[AnalyticsCategory.PERFORMANCE]
    check("3. Performance engine works",
          perf.metric("completion_performance") is not None
          and perf.metric("operational_efficiency") is not None)

    quality = A[AnalyticsCategory.QUALITY]
    check("4. Quality engine works",
          quality.metric("workflow_quality") is not None
          and quality.metric("graph_integrity").value == 1.0)

    trend = A[AnalyticsCategory.TREND]
    check("5. Trend engine works",
          trend.metric("operational_trend") is not None
          and all(-1.0 <= m.value <= 1.0 for m in trend.metrics))

    risk = A[AnalyticsCategory.RISK]
    check("6. Risk engine works",
          risk.metric("operational_risk") is not None
          and all(m.dimension == "risk" and 0.0 <= m.value <= 1.0 for m in risk.metrics))

    # --- V3-P5 registry / lineage / validation (7-9) ------------------------
    check("7. Analytics registry works",
          all(oa.registry.exists(r.analytics_id) for r in A.values())
          and len(oa.registry.list_analytics()) == len(A))
    check("8. Analytics lineage works",
          all(tracker.verify_chain(r.lineage_id) for r in A.values())
          and {"analytics", "workflow", "event", "case", "patient"}
          <= {n.kind for n in tracker.chain(A[AnalyticsCategory.RISK].lineage_id)})
    check("9. Analytics validation works",
          all(oa.validate(r).ok for r in A.values()))

    # --- V3-P6 recommendation engines (10-14) -------------------------------
    cid = fx.recommendation_records["guidance"][0].context_id
    ctx = orr.registry.context(cid)
    check("10. Recommendation context engine works",
          bool(ctx.analytics_context and ctx.workflow_context and ctx.graph_context
               and ctx.risk_context and ctx.health_context))

    guidance = fx.recommendation_records["guidance"]
    check("11. Guidance engine works",
          len(guidance) >= 1 and all(g.n_evidence > 0 and g.statement and g.rationale
                                     for g in guidance))

    check("12. Prioritization engine works",
          level_for_score(0.9) == PriorityLevel.CRITICAL
          and level_for_score(0.1) == PriorityLevel.LOW
          and all(level_for_score(r.priority.score) == r.priority.level and r.priority.reason
                  for r in recs))

    opt = fx.recommendation_records["optimization"]
    check("13. Optimization engine works",
          len(opt) >= 1 and all(o.kind == RecommendationKind.OPTIMIZATION
                                and "Suggestion" in o.statement for o in opt))

    esc = fx.recommendation_records["escalation"]
    check("14. Escalation framework works",
          len(esc) >= 1 and all("no automatic escalation" in e.statement.lower()
                                and any(ev.metric_name == "risk_context" for ev in e.evidence)
                                for e in esc))

    # --- V3-P6 registry / lineage / validation (15-17) ----------------------
    check("15. Recommendation registry works",
          all(orr.registry.exists(r.recommendation_id) for r in recs)
          and len(orr.registry.list_recommendations()) == len(recs))
    check("16. Recommendation lineage works",
          all(tracker.verify_chain(r.lineage_id) for r in recs)
          and {"recommendation", "analytics", "workflow", "event", "case", "patient"}
          <= {n.kind for n in tracker.chain(recs[0].lineage_id)})
    check("17. Recommendation validation works",
          all(orr.validate(r).ok for r in recs))


    # --- suite / gates / lineage / boundaries (18-22) -----------------------
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q",
                           "tests/test_operational_analytics.py",
                           "tests/test_operational_recommendations.py",
                           "tests/test_v3_p5_p6_e2e.py", "tests/test_boundaries.py"],
                          cwd=str(REPO), capture_output=True, text=True)
    check("18. All tests pass", proc.returncode == 0,
          (proc.stdout.strip().splitlines() or [""])[-1])

    # governance gates: re-affirm with a fresh fixture + reject malformed artifacts.
    fresh = build_v3c(2)
    analytics_gate_ok = all(fresh.analytics.validate(r).ok
                            for r in fresh.analytics_records.values())
    rec_gate_ok = all(fresh.recommendations.validate(r).ok
                      for r in all_recommendations(fresh))
    # the analytics gate must reject an underived record (no sources)
    a_gate = AnalyticsGovernanceGate()
    underived = AnalyticsRecord(
        analytics_id="analytics+" + "0" * 16, category="metrics",
        scope="metrics:operational:all", subject_kind="operational", subject_id="all",
        metrics=(AnalyticsMetric("x", 0.5, "ratio", True, "metrics", "explained"),), sources=())
    a_reject = not a_gate.evaluate(record=underived, parents=(), requires_lineage=False).ok
    # the recommendation gate must reject a black-box record (no evidence/analytics)
    from backend.operational_recommendations import RecommendationRecord, RecommendationPriority
    blackbox = RecommendationRecord(
        recommendation_id="recommendation+" + "0" * 16, kind="guidance",
        scope="guidance:workflow:all", subject_kind="workflow", subject_id="all",
        statement="x", priority=RecommendationPriority("medium", 0.3, "r"), evidence=(),
        analytics_ids=(), rationale="r")
    r_reject = not RecommendationGovernanceGate().evaluate(
        record=blackbox, parents=(), requires_lineage=False).ok
    check("19. Governance gates pass",
          analytics_gate_ok and rec_gate_ok and a_reject and r_reject)

    # V3 workflow lineage intact (analytics/recs only read workflows)
    wf_ok = all(tracker.verify_chain(w.lineage_id) for w in fx.base.workflow_records.values())
    check("20. Version 3 workflow lineage remains intact", wf_ok)

    # V3 graph lineage intact
    graph_ok = all(tracker.verify_chain(fx.base.graph.registry.node(n).lineage_id)
                   for n in fx.base.graph.registry.list_nodes())
    check("21. Version 3 graph lineage remains intact", graph_ok)

    bnd = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_boundaries.py"],
                         cwd=str(REPO), capture_output=True, text=True)
    check("22. No architectural boundary violations exist", bnd.returncode == 0,
          (bnd.stdout.strip().splitlines() or [""])[-1])

    print("\nV3-P5 + V3-P6 FINAL VALIDATION")
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
