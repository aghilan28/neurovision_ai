"""Tests for the Temporal Intelligence Layer (V3-P2).

Covers the timeline engine, history reconstruction, state evolution, temporal
analytics, the temporal registry/audit/lineage/validation, visualization
contracts, determinism, and that artifacts are derived from events (no hidden
state reconstruction) with lineage back to the patient.
"""

from __future__ import annotations

import pytest

from backend.temporal_intelligence import TemporalIntelligenceService

from tests._v3_helpers import build_v3


@pytest.fixture(scope="module")
def fx():
    return build_v3(2)


@pytest.fixture()
def ti(fx):
    return TemporalIntelligenceService(fx.events).load_events(fx.all_events)


def _case_sources(fx, case_id):
    review_ids = [r.review_id for r in fx.reviews.values() if r.case_id == case_id]
    finding_ids = [f.finding_id for f in fx.findings.values() if f.case_id == case_id]
    return [case_id] + review_ids + finding_ids


# --- timeline engine ----------------------------------------------------------
def test_timeline_is_ordered_and_reproducible(fx, ti):
    case_id = next(iter(fx.cases))
    tl = ti.build_timeline(subject_kind="case", subject_id=case_id,
                           source_entity_ids=_case_sources(fx, case_id))
    assert tl.length > 0
    assert [p.order for p in tl.points] == list(range(tl.length))
    ti2 = TemporalIntelligenceService(fx.events).load_events(fx.all_events)
    tl2 = ti2.build_timeline(subject_kind="case", subject_id=case_id,
                             source_entity_ids=_case_sources(fx, case_id))
    assert tl.state_signature() == tl2.state_signature()
    assert tl.timeline_id == tl2.timeline_id


def test_operational_timeline_spans_all_events(fx, ti):
    tl = ti.build_operational_timeline()
    assert tl.length == len(fx.all_events)


# --- history ------------------------------------------------------------------
def test_history_reconstruction(fx, ti):
    case_id = next(iter(fx.cases))
    h = ti.build_history(subject_kind="case", subject_id=case_id,
                         source_entity_ids=_case_sources(fx, case_id))
    assert h.length > 0
    assert [e.order for e in h.entries] == list(range(h.length))
    # every entry carries a source version (recoverable version history)
    assert all(e.source_version for e in h.entries)


# --- evolution ----------------------------------------------------------------
def test_state_evolution_is_continuous(fx, ti):
    case_id = next(iter(fx.cases))
    ev = ti.build_evolution(subject_kind="case", subject_id=case_id, source_entity_ids=[case_id])
    states = [(s.from_state, s.to_state) for s in ev.steps]
    assert states[0][0] is None                       # first transition has no predecessor
    # continuity: each step's from_state equals the previous to_state
    for prev, cur in zip(ev.steps, ev.steps[1:]):
        assert cur.from_state == prev.to_state
    assert ev.steps[-1].to_state in ("reviewed", "closed", "archived")


# --- temporal analytics -------------------------------------------------------
def test_temporal_analytics_durations_in_logical_steps(fx, ti):
    an = ti.build_analytics(scope="operational")
    case_metric = an.metric("case_lifecycle_steps")
    assert case_metric is not None and case_metric.observed and case_metric.steps >= 0
    total = an.metric("operational_event_total")
    assert total.steps == len(fx.all_events)
    # unobserved metric reports steps == -1
    dec = an.metric("decision_latency_steps")
    assert dec is not None and (dec.observed or dec.steps == -1)


# --- registry / audit / lineage / validation ---------------------------------
def test_no_artifact_outside_registry_and_validation_passes(fx, ti):
    case_id = next(iter(fx.cases))
    tl = ti.build_timeline(subject_kind="case", subject_id=case_id,
                           source_entity_ids=_case_sources(fx, case_id))
    h = ti.build_history(subject_kind="case", subject_id=case_id,
                         source_entity_ids=_case_sources(fx, case_id))
    ev = ti.build_evolution(subject_kind="case", subject_id=case_id, source_entity_ids=[case_id])
    an = ti.build_analytics(scope="operational")
    for art, kind in [(tl, "timeline"), (h, "history"), (ev, "evolution"),
                      (an, "temporal_analytics")]:
        assert ti.registry.exists(art.__dict__[
            "timeline_id" if kind == "timeline" else
            "history_id" if kind == "history" else
            "evolution_id" if kind == "evolution" else "analytics_id"])
        assert ti.validate(art, kind).ok, ti.validate(art, kind).to_dict()
    assert ti.audit.verify()


def test_temporal_lineage_traces_to_patient(fx, ti):
    case_id = next(iter(fx.cases))
    tl = ti.build_timeline(subject_kind="case", subject_id=case_id,
                           source_entity_ids=_case_sources(fx, case_id))
    kinds = {r.kind for r in fx.cs.lineage.chain(tl.lineage_id)}
    assert {"timeline", "event", "case", "patient"} <= kinds
    assert fx.cs.lineage.verify_chain(tl.lineage_id)


# --- visualization contracts --------------------------------------------------
def test_visualization_contracts_exist(fx, ti):
    case_id = next(iter(fx.cases))
    tl = ti.build_timeline(subject_kind="case", subject_id=case_id,
                           source_entity_ids=_case_sources(fx, case_id))
    ev = ti.build_evolution(subject_kind="case", subject_id=case_id, source_entity_ids=[case_id])
    an = ti.build_analytics(scope="operational")
    contracts = ti.visualization_contracts(timeline=tl, evolution=ev, analytics=an)
    types = {c["contract_type"] for c in contracts}
    assert types == {"timeline", "event_sequence", "evolution_graph", "duration_graph",
                     "trend_graph", "operational_dashboard"}


# --- derived-from-events guard ------------------------------------------------
def test_artifact_must_be_derived_from_events(fx):
    from backend.temporal_intelligence.validation import TemporalGovernanceGate
    from backend.temporal_intelligence.models import Timeline
    empty = Timeline(timeline_id="timeline+" + "0" * 16, scope="case:x", subject_kind="case",
                     subject_id="x", points=())
    gate = TemporalGovernanceGate()
    report = gate.evaluate(artifact=empty, kind="timeline", parents=(), derived_from_events=False)
    assert not report.ok
    assert "risk_validation" in {c.name for c in report.failures()}
