"""Tests for the Governance Intelligence Layer (V4-P7).

Verifies that governance intelligence is derived, deterministic, traceable, audited,
explainable, and observation-only (it never modifies governance). Uses the shared
V4-P7 fixture (`build_v4d`) over the one platform lineage tracker.
"""

from __future__ import annotations

import re

import pytest

from _v4d_helpers import build_v4d, active_policies
from _v4c_helpers import goals, plans, tasks, agents, executions

from backend.governance_intelligence import (
    GovernanceIntelligenceGate, GovernanceIntelligenceError,
    GovernedObservation, GovernedKind, ViolationType, RISK_DIMENSIONS, GOVERNED_KINDS,
    detect_violations, build_escalations, approval_metrics,
    monitoring_summary, risk_summary, GovernanceIntelligenceRecord,
)
from backend.governance_intelligence.schemas import all_contracts, validate_entity


@pytest.fixture(scope="module")
def fx():
    return build_v4d(2)


@pytest.fixture(scope="module")
def record(fx):
    return fx.intelligence


# --- identity + build ---------------------------------------------------------
def test_intelligence_identity_is_content_addressed(record):
    assert re.match(r"^govintel\+[0-9a-f]{16}$", record.intelligence_id)
    assert record.scope == "operational"
    assert record.n_observed == len(record.approvals) > 0


def test_observes_every_governed_kind(record):
    # goals, policies, plans, tasks, agents, executions all observed
    assert set(record.observed_kinds) <= GOVERNED_KINDS
    for kind in (GovernedKind.GOAL, GovernedKind.POLICY, GovernedKind.PLAN,
                 GovernedKind.TASK, GovernedKind.AGENT, GovernedKind.EXECUTION):
        assert kind in record.observed_kinds


# --- 1. approval intelligence -------------------------------------------------
def test_approval_intelligence(record):
    assert len(record.approvals) == record.n_observed
    m = approval_metrics(record.approvals)
    assert m["n_approvals"] == record.n_observed
    assert 0.0 <= m["approval_health"] <= 1.0
    assert m["throughput"] >= 1
    # latency is logical (non-negative integer steps)
    assert all(a.latency_steps >= 0 for a in record.approvals)


# --- 2. violation intelligence ------------------------------------------------
def test_no_violations_on_clean_platform(record):
    assert record.violations == ()


def test_violation_detection_flags_bad_state():
    bad = GovernedObservation(
        kind=GovernedKind.EXECUTION, entity_id="execution+deadbeefdeadbeef",
        approval_state="denied", decision="denied", authority=None, history=(),
        escalation_required=False, escalated=False, policy_references=(), state="active",
        lineage_id="lineage+0000000000000000", live=True)
    violations = detect_violations([bad])
    types = {v.violation_type for v in violations}
    # live-without-approval (lifecycle) + denied authorization
    assert ViolationType.LIFECYCLE in types
    assert ViolationType.AUTHORIZATION in types
    assert all(re.match(r"^govviolation\+[0-9a-f]{16}$", v.violation_id) for v in violations)


# --- 3. escalation intelligence -----------------------------------------------
def test_escalation_intelligence():
    esc_obs = GovernedObservation(
        kind=GovernedKind.AGENT, entity_id="agent+1111111111111111",
        approval_state="escalated", decision="escalated", authority="gov",
        history=({"decision": "escalated"},), escalation_required=True, escalated=True,
        policy_references=("p1",), state="under_review", lineage_id="lineage+1111111111111111",
        live=False)
    recs = build_escalations([esc_obs])
    assert len(recs) == 1
    assert recs[0].requested and recs[0].outcome in ("pending", "unresolved")
    assert recs[0].delay_steps >= 0


# --- 4. governance risk engine ------------------------------------------------
def test_risk_engine_explainable_and_bounded(record):
    assert record.risks
    assert all(0.0 <= r.score <= 1.0 for r in record.risks)
    assert all(r.dimension in RISK_DIMENSIONS for r in record.risks)
    assert all(r.factors and r.explanation for r in record.risks)  # explainable
    summary = risk_summary(record.risks)
    assert 0.0 <= summary["overall_mean_score"] <= 1.0


# --- 5. governance analytics --------------------------------------------------
def test_governance_analytics(record):
    names = {m.name for m in record.metrics}
    assert {"governance_health", "approval_health", "n_violations", "overall_risk"} <= names
    assert 0.0 <= record.health_score <= 1.0


# --- 6. governance registry ---------------------------------------------------
def test_registry_tracks_record_and_indexes(fx, record):
    reg = fx.governance.registry
    assert reg.exists(record.intelligence_id)
    assert len(reg.list_approvals()) == len(record.approvals)
    assert len(reg.list_risks()) == len(record.risks)
    assert len(reg.list_metrics()) == len(record.metrics)


# --- 7. governance lineage (reaches patient) ----------------------------------
def test_lineage_reaches_patient(fx, record):
    assert fx.tracker.verify_chain(record.lineage_id)
    kinds = {r.kind for r in fx.tracker.chain(record.lineage_id)}
    assert {"governance_intelligence", "goal", "policy", "plan", "task", "agent",
            "execution", "patient"} <= kinds


# --- 8. governance validation -------------------------------------------------
def test_validation_passes_all_dimensions(fx, record):
    report = fx.governance.validate(record)
    assert report.ok
    names = {c.name for c in report.checks}
    assert {"identity_integrity", "approval_integrity", "violation_integrity",
            "escalation_integrity", "risk_integrity", "registry_integrity",
            "audit_integrity", "lineage_integrity", "version_integrity"} <= names


# --- monitoring ---------------------------------------------------------------
def test_monitoring_clear_on_clean_platform(fx, record):
    mon = fx.governance.monitoring(record)
    assert mon["clear"]
    assert mon["n_executions_requiring_intervention"] == 0


def test_monitoring_flags_blocked_execution():
    blocked = GovernedObservation(
        kind=GovernedKind.EXECUTION, entity_id="execution+2222222222222222",
        approval_state="authorized", decision="permitted", authority="gov", history=(),
        escalation_required=False, escalated=False, policy_references=("p1",), state="blocked",
        lineage_id="lineage+2222222222222222", live=True)
    summary = monitoring_summary([blocked])
    assert summary["n_executions_requiring_intervention"] == 1


# --- audit + determinism ------------------------------------------------------
def test_audit_chain_verifies(fx):
    assert fx.governance.audit.verify()


def test_build_is_deterministic():
    a = build_v4d(2).intelligence
    b = build_v4d(2).intelligence
    assert a.intelligence_id == b.intelligence_id
    assert a.state_signature() == b.state_signature()
    assert a.version == b.version
    assert a.health_score == b.health_score


# --- observe-only invariant ---------------------------------------------------
def test_intelligence_does_not_modify_governance():
    """Building governance intelligence must not mutate any observed entity's state."""
    fx = build_v4d(2)
    before = [(a.agent_id, a.governance.approval_state, a.state.value)
              for a in agents(fx.base)]
    # rebuild intelligence again over the same records
    fx.governance.load_sources(
        goals=goals(fx.base), policies=active_policies(fx.base), plans=plans(fx.base),
        tasks=tasks(fx.base), agents=agents(fx.base), executions=executions(fx.base))
    fx.governance.build(scope="operational")
    after = [(a.agent_id, a.governance.approval_state, a.state.value)
             for a in agents(fx.base)]
    assert before == after


# --- governance gate ----------------------------------------------------------
def test_gate_rejects_unbounded_health():
    gate = GovernanceIntelligenceGate()
    bad = GovernanceIntelligenceRecord(
        intelligence_id="govintel+deadbeefdeadbeef", scope="operational",
        health_score=2.0, n_observed=0, observed_kinds=())
    report = gate.evaluate(record=bad, parents=(), requires_lineage=False)
    assert not report.ok
    with pytest.raises(GovernanceIntelligenceError):
        gate.raise_if_failed(report)


# --- contracts ----------------------------------------------------------------
def test_entity_contracts_present_and_validate():
    contracts = all_contracts()["contracts"]
    for name in ("GovernanceIntelligenceRecord", "ApprovalRecord", "ViolationRecord",
                 "EscalationRecord", "GovernanceRiskRecord", "GovernanceMetric"):
        assert name in contracts
    ok, missing = validate_entity("ApprovalRecord",
                                  {"approval_id": "x", "entity_kind": "goal",
                                   "entity_id": "g", "approval_state": "approved"})
    assert ok and not missing


# --- reports ------------------------------------------------------------------
def test_reports_generate(fx, record):
    reports = fx.governance.reports(record)
    for key in ("governance_summary_report", "approval_report", "violation_report",
                "escalation_report", "governance_risk_report", "governance_analytics_report",
                "governance_audit_report", "governance_lineage_report"):
        assert key in reports
    assert reports["governance_audit_report"]["verified"]
    assert reports["governance_lineage_report"]["lineage_verified"]
