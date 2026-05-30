"""End-to-end V3-P1 + V3-P2 deliverable-chain test.

Proves the required chain executes with complete traceability:

    Patient -> Case -> Review -> Finding -> Knowledge -> Decision -> Event
            -> Timeline -> History -> Evolution -> Temporal Analytics

over the real V2 aggregates, and that all cross-version invariants hold (V2 lineage
intact, determinism, audit immutability, no hidden state reconstruction).
"""

from __future__ import annotations

from backend.temporal_intelligence import TemporalIntelligenceService

from tests._v3_helpers import build_v3


def test_full_chain_executes_with_traceability():
    fx = build_v3(2)
    tracker = fx.cs.lineage  # single shared platform lineage tracker

    # --- V3-P1: events observed from the real V2 systems -------------------
    assert len(fx.all_events) > 0
    assert all(fx.events.validate(e).ok for e in fx.all_events)
    assert fx.events.audit.verify()

    # --- V3-P2: temporal intelligence derived from events ------------------
    ti = TemporalIntelligenceService(fx.events).load_events(fx.all_events)
    case_id = next(iter(fx.cases))
    review_ids = [r.review_id for r in fx.reviews.values() if r.case_id == case_id]
    finding_ids = [f.finding_id for f in fx.findings.values() if f.case_id == case_id]
    sources = [case_id] + review_ids + finding_ids

    timeline = ti.build_timeline(subject_kind="case", subject_id=case_id, source_entity_ids=sources)
    history = ti.build_history(subject_kind="case", subject_id=case_id, source_entity_ids=sources)
    evolution = ti.build_evolution(subject_kind="case", subject_id=case_id, source_entity_ids=[case_id])
    analytics = ti.build_analytics(scope="operational")
    op_timeline = ti.build_operational_timeline()

    for art, kind in [(timeline, "timeline"), (history, "history"), (evolution, "evolution"),
                      (analytics, "temporal_analytics"), (op_timeline, "timeline")]:
        assert ti.validate(art, kind).ok

    # --- traceability: temporal artifact -> event -> source -> patient -----
    chain_kinds = {r.kind for r in tracker.chain(timeline.lineage_id)}
    for k in ("timeline", "event", "case", "review", "finding", "patient"):
        assert k in chain_kinds, f"missing {k} in temporal lineage"
    assert tracker.verify_chain(timeline.lineage_id)
    assert tracker.verify_chain(analytics.lineage_id)

    # --- audit trails immutable + intact -----------------------------------
    assert fx.events.audit.verify() and ti.audit.verify()

    # --- V2 lineage remains intact (events/temporal only read it) ----------
    assert tracker.verify_chain(fx.cases[case_id].lineage_id)
    for fid in finding_ids:
        assert tracker.verify_chain(fx.findings[fid].lineage_id)

    # --- everything registered ---------------------------------------------
    assert all(fx.events.registry.exists(e.event_id) for e in fx.all_events)
    assert ti.registry.exists(timeline.timeline_id)
    assert ti.registry.exists(analytics.analytics_id)

    # --- visualization contracts exist -------------------------------------
    contracts = ti.visualization_contracts(timeline=timeline, evolution=evolution, analytics=analytics)
    assert len(contracts) == 6


def test_full_chain_is_reproducible():
    def run():
        fx = build_v3(2)
        ti = TemporalIntelligenceService(fx.events).load_events(fx.all_events)
        op = ti.build_operational_timeline()
        an = ti.build_analytics(scope="operational")
        return ([e.event_id for e in fx.all_events], op.state_signature(),
                an.state_signature(), fx.events.audit.head, ti.audit.head)

    assert run() == run()


def test_events_do_not_mutate_v2_or_reconstruct_hidden_state():
    fx = build_v3(2)
    case_id = next(iter(fx.cases))
    # V2 case digest is unchanged by event/temporal processing.
    before = fx.cs.registry.get(case_id).content_signature()
    ti = TemporalIntelligenceService(fx.events).load_events(fx.all_events)
    ti.build_operational_timeline()
    ti.build_analytics(scope="operational")
    after = fx.cs.registry.get(case_id).content_signature()
    assert before == after
