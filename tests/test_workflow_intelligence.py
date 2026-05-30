"""Tests for the Workflow Intelligence Layer (V3-P3).

Covers the workflow registry, transition engine, dependency engine, bottleneck
analysis, efficiency analytics, workflow lineage, validation, determinism, and the
governance gate — over workflows derived from real events.
"""

from __future__ import annotations

import pytest

from backend.workflow_intelligence import (
    WorkflowGovernanceGate, WorkflowRegistry,
    derive_transitions, transition_frequencies,
)
from backend.workflow_intelligence.dependencies import EntityRef, derive_dependencies

from _v3b_helpers import build_v3b, _entity_refs


@pytest.fixture(scope="module")
def fx():
    return build_v3b(2)


def _case_workflow(fx):
    case_id = next(iter(fx.base.cases))
    for wf in fx.workflow_records.values():
        if wf.subject_id == case_id and wf.workflow_type == "case_workflow":
            return wf
    raise AssertionError("no case workflow")


# --- registry -----------------------------------------------------------------
def test_no_workflow_outside_registry(fx):
    for wid, wf in fx.workflow_records.items():
        assert fx.workflows.registry.exists(wid)
        assert fx.workflows.registry.get(wid).version == wf.version


def test_registry_rejects_silent_overwrite():
    from backend.workflow_intelligence.models import WorkflowRegistryRecord
    reg = WorkflowRegistry()
    rec = WorkflowRegistryRecord(workflow_id="workflow+" + "a" * 16, workflow_type="case_workflow",
                                 subject_id="case+x", state="reviewed", version="v1",
                                 lineage_id="lineage+" + "b" * 16, audit_state="h",
                                 content_signature_value="sig-1")
    reg.register(rec)
    bad = WorkflowRegistryRecord(workflow_id="workflow+" + "a" * 16, workflow_type="case_workflow",
                                 subject_id="case+x", state="reviewed", version="v1",
                                 lineage_id="lineage+" + "b" * 16, audit_state="h",
                                 content_signature_value="sig-2")
    with pytest.raises(ValueError):
        reg.register(bad)


# --- transition engine --------------------------------------------------------
def test_transition_engine(fx):
    wf = _case_workflow(fx)
    states = [t.to_state for t in wf.transitions]
    assert states[0] == "created" and "reviewed" in states
    # continuity: each from_state == previous to_state
    for prev, cur in zip(wf.transitions, wf.transitions[1:]):
        assert cur.from_state == prev.to_state
    freqs = transition_frequencies(wf.transitions)
    assert "START->created" in freqs


def test_transition_derivation_is_pure():
    # no events -> no transitions
    assert derive_transitions([]) == []


# --- dependency engine --------------------------------------------------------
def test_dependency_engine_relations(fx):
    case_id = next(iter(fx.base.cases))
    deps = derive_dependencies(_entity_refs(fx.base, case_id))
    relations = {d.relation for d in deps}
    assert relations <= {"upstream", "downstream", "blocked", "waiting", "completed"}
    # case->review downstream and review->case upstream/completed both present
    kinds = {(d.from_kind, d.to_kind) for d in deps}
    assert ("case", "review") in kinds


def test_dependency_blocked_and_waiting():
    refs = [EntityRef("case+a", "case", None, completed=False),
            EntityRef("review+b", "review", "case+a", completed=False)]
    deps = derive_dependencies(refs)
    rels = {d.relation for d in deps}
    assert "blocked" in rels        # parent not complete -> child blocked
    assert "waiting" in rels        # child waits on incomplete parent


# --- bottleneck + efficiency --------------------------------------------------
def test_efficiency_metrics_present_and_bounded(fx):
    wf = _case_workflow(fx)
    names = {m.name for m in wf.metrics}
    assert {"completion_rate", "rework_rate", "throughput", "operational_velocity",
            "workflow_health_score"} <= names
    for m in wf.metrics:
        if m.unit == "ratio":
            assert 0.0 <= m.value <= 1.0
    assert wf.metric("completion_rate").value == 1.0   # case reached 'reviewed'


def test_bottleneck_detection_on_clean_workflow(fx):
    wf = _case_workflow(fx)
    # a clean linear case workflow has no rework/stall
    assert "repeated_rework" not in wf.metadata.bottlenecks
    assert "workflow_stall" not in wf.metadata.bottlenecks


# --- lineage / validation / determinism ---------------------------------------
def test_workflow_lineage_traces_to_patient(fx):
    wf = _case_workflow(fx)
    kinds = {r.kind for r in fx.base.cs.lineage.chain(wf.lineage_id)}
    assert {"workflow", "event", "case", "patient"} <= kinds
    assert fx.base.cs.lineage.verify_chain(wf.lineage_id)


def test_full_workflow_validation_passes(fx):
    for wf in fx.workflow_records.values():
        rep = fx.workflows.validate(wf).to_dict()
        names = {c["name"] for c in rep["checks"]}
        assert {"transition_integrity", "dependency_integrity", "metric_integrity",
                "registry_integrity", "audit_integrity", "lineage_integrity",
                "version_integrity"} <= names
        assert rep["ok"], rep


def test_governance_gate_rejects_underived_workflow():
    from backend.workflow_intelligence.models import WorkflowRecord
    empty = WorkflowRecord(workflow_id="workflow+" + "0" * 16, workflow_type="case_workflow",
                           subject_kind="case", subject_id="case+x", state="empty")
    gate = WorkflowGovernanceGate()
    report = gate.evaluate(workflow=empty, parents=(), derived_from_events=False)
    assert not report.ok
    assert "risk_validation" in {c.name for c in report.failures()}


def test_workflow_audit_verifies(fx):
    assert fx.workflows.audit.verify()
    assert len(fx.workflows.audit) > 0


def test_workflow_is_reproducible():
    a = build_v3b(2)
    b = build_v3b(2)
    a_sigs = sorted(w.state_signature() for w in a.workflow_records.values())
    b_sigs = sorted(w.state_signature() for w in b.workflow_records.values())
    assert a_sigs == b_sigs
