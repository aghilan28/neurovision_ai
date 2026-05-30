"""End-to-end V3-P5 + V3-P6 deliverable-chain test.

Proves the required chain executes with complete traceability:

    Patient -> Case -> Review -> Finding -> Knowledge -> Decision -> Event
            -> Timeline -> Workflow -> Graph -> Operational Analytics
            -> Operational Risks -> Operational Recommendations

over the real V2/V3 artifacts, and that all cross-version invariants hold (V2 + V3
event/temporal/workflow/graph lineage intact, determinism, audit immutability,
analytics-never-a-source-of-truth, no black-box recommendations, no execution).
"""

from __future__ import annotations

from _v3c_helpers import build_v3c, all_recommendations


def test_full_chain_executes_with_traceability():
    fx = build_v3c(2)
    tracker = fx.base.base.cs.lineage   # single shared platform lineage tracker

    # --- V3-P5 analytics validate + trace to patient -----------------------
    for rec in fx.analytics_records.values():
        assert fx.analytics.validate(rec).ok
        kinds = {r.kind for r in tracker.chain(rec.lineage_id)}
        assert {"analytics", "workflow", "graph_node", "event", "case", "patient"} <= kinds
        assert tracker.verify_chain(rec.lineage_id)

    # operational risks exist (the risk dimension of analytics)
    risk = fx.analytics_records["risk"]
    assert any(m.name == "operational_risk" for m in risk.metrics)

    # --- V3-P6 recommendations validate + trace to patient -----------------
    recs = all_recommendations(fx)
    assert recs
    for rec in recs:
        assert fx.recommendations.validate(rec).ok
        kinds = {r.kind for r in tracker.chain(rec.lineage_id)}
        # the complete chain link: recommendation -> analytics -> workflow/graph ->
        # event -> case -> patient
        for k in ("recommendation", "analytics", "workflow", "event", "case", "patient"):
            assert k in kinds, f"missing {k} in recommendation lineage"
        assert tracker.verify_chain(rec.lineage_id)

    # --- audit trails immutable + intact -----------------------------------
    assert fx.analytics.audit.verify()
    assert fx.recommendations.audit.verify()
    assert fx.base.workflows.audit.verify() and fx.base.graph.audit.verify()
    assert fx.base.base.events.audit.verify()

    # --- V2 + V3 (event/temporal/workflow/graph) lineage remains intact -----
    for c in fx.base.base.cases.values():
        assert tracker.verify_chain(c.lineage_id)
    for e in fx.base.base.all_events:
        assert tracker.verify_chain(e.lineage_id)
    for wf in fx.base.workflow_records.values():
        assert tracker.verify_chain(wf.lineage_id)
    for nid in fx.base.graph.registry.list_nodes():
        assert tracker.verify_chain(fx.base.graph.registry.node(nid).lineage_id)

    # --- everything registered ---------------------------------------------
    assert all(fx.analytics.registry.exists(r.analytics_id)
               for r in fx.analytics_records.values())
    assert all(fx.recommendations.registry.exists(r.recommendation_id) for r in recs)


def test_recommendations_link_to_analytics_and_evidence():
    """No black-box recommendations: each links to analytics + cites evidence."""
    fx = build_v3c(2)
    for rec in all_recommendations(fx):
        assert rec.analytics_ids                       # analytics-linked
        assert rec.n_evidence > 0                      # evidence-linked
        # every cited analytics id is a real registered analytics record
        for aid in rec.analytics_ids:
            assert fx.analytics.registry.exists(aid)


def test_full_chain_is_reproducible():
    def run():
        fx = build_v3c(2)
        a_sigs = sorted(r.state_signature() for r in fx.analytics_records.values())
        r_sigs = sorted(r.state_signature() for r in all_recommendations(fx))
        return (a_sigs, r_sigs, fx.analytics.audit.head, fx.recommendations.audit.head)

    assert run() == run()


def test_analytics_and_recommendations_do_not_mutate_sources():
    fx = build_v3c(2)
    case_id = next(iter(fx.base.base.cases))
    before = fx.base.base.cs.registry.get(case_id).content_signature()
    # re-deriving analytics + a fresh context must not change source truth
    fx.analytics.build_operational()
    fx.recommendations.build_context(scope="operational:recheck")
    after = fx.base.base.cs.registry.get(case_id).content_signature()
    assert before == after


def test_no_autonomous_execution_or_auto_escalation():
    """Recommendations are suggestions; escalation is a candidate, never automatic."""
    fx = build_v3c(2)
    for rec in fx.recommendation_records["escalation"]:
        assert "no automatic escalation" in rec.statement.lower()
    # the service exposes no execute/apply/act API
    svc = fx.recommendations
    for forbidden in ("execute", "apply", "act", "escalate_now", "run"):
        assert not hasattr(svc, forbidden)
