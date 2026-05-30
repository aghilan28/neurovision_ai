"""Tests for the Planning Foundation (V4-P3).

Covers the plan taxonomy, registry, lifecycle (legal + forbidden transitions),
dependencies (versioned + acyclic), governance, goal->plan derivation, lineage to
the patient, validation (8 dimensions), determinism, and audit immutability.
"""

from __future__ import annotations

import pytest

from backend.planning_foundation import (
    PlanService, PlanMetadata, PlanCategory, PlanPriority, PlanLifecycleState,
    PlanLifecycleError, PlanGovernanceError, PlanDerivationError, PlanRegistry,
    mint_plan, validate_identity, is_category, ancestry, has_cycle, PLAN_CATEGORIES,
)
from backend.planning_foundation.models import PlanRegistryRecord, PlanDependency

from _v4b_helpers import build_v4b, goals, plans


@pytest.fixture(scope="module")
def fx():
    return build_v4b(2)


def _fresh_plan(svc, goal):
    return svc.create_plan(category=PlanCategory.WORKFLOW, plan_key="k",
                           metadata=PlanMetadata(title="T", approach="a", expected_outcome="o"),
                           source_goal_id=goal.goal_id, source_goal_lineage_id=goal.lineage_id,
                           source_goal_state=goal.state.value, priority=PlanPriority.MEDIUM)


# --- taxonomy -----------------------------------------------------------------
def test_plan_taxonomy_is_hierarchical():
    assert is_category(PlanCategory.WORKFLOW)
    chain = ancestry(PlanCategory.WORKFLOW)
    assert chain[-1] == PlanCategory.STRATEGIC          # apex
    assert PlanCategory.OPERATIONAL in chain
    assert len(PLAN_CATEGORIES) >= 8


def test_unknown_category_rejected(fx):
    g = goals(fx)[0]
    with pytest.raises(Exception):
        fx.plans.create_plan(category="nope", plan_key="k",
                             metadata=PlanMetadata(title="T", approach="a"),
                             source_goal_id=g.goal_id, source_goal_lineage_id=g.lineage_id,
                             source_goal_state=g.state.value)


# --- identity -----------------------------------------------------------------
def test_plan_identity_is_deterministic():
    a = mint_plan("workflow", "goal+" + "a" * 16, "cut-latency")
    b = mint_plan("workflow", "goal+" + "a" * 16, "cut-latency")
    assert a.id == b.id and validate_identity(a.id)[0]


# --- registry -----------------------------------------------------------------
def test_no_plan_outside_registry(fx):
    for p in plans(fx):
        assert fx.plans.registry.exists(p.plan_id)
        assert fx.plans.registry.get(p.plan_id).version == p.version


def test_registry_rejects_silent_overwrite():
    reg = PlanRegistry()
    rec = PlanRegistryRecord(plan_id="plan+" + "a" * 16, category="workflow",
                             source_goal_id="goal+" + "c" * 16, state="proposed", priority="high",
                             version="v1", approval_state="pending", dependencies=(),
                             goal_references=(), policy_references=(),
                             lineage_id="lineage+" + "b" * 16, audit_state="h",
                             content_signature_value="sig-1")
    reg.register(rec)
    bad = PlanRegistryRecord(plan_id="plan+" + "a" * 16, category="workflow",
                             source_goal_id="goal+" + "c" * 16, state="proposed", priority="high",
                             version="v1", approval_state="pending", dependencies=(),
                             goal_references=(), policy_references=(),
                             lineage_id="lineage+" + "b" * 16, audit_state="h",
                             content_signature_value="sig-2")
    with pytest.raises(ValueError):
        reg.register(bad)


# --- goal -> plan integration -------------------------------------------------
def test_every_plan_derives_from_a_goal(fx):
    goal_ids = {g.goal_id for g in goals(fx)}
    for p in plans(fx):
        assert p.source_goal_id in goal_ids


def test_cannot_derive_plan_from_unapproved_goal():
    from _v4_helpers import build_v4
    base = build_v4(1, activate=False)          # goals stay PROPOSED
    g = list(base.goals.registry.list_goals())[0]
    grec = base.goals.registry.get(g)
    svc = PlanService(lineage_tracker=base.tracker)
    with pytest.raises(PlanDerivationError):
        svc.create_plan(category=PlanCategory.WORKFLOW, plan_key="k",
                        metadata=PlanMetadata(title="T", approach="a"),
                        source_goal_id=g, source_goal_lineage_id=grec.lineage_id,
                        source_goal_state="proposed")


# --- lifecycle ----------------------------------------------------------------
def test_plan_lifecycle_reaches_ready(fx):
    for p in plans(fx):
        assert p.state == PlanLifecycleState.READY
        assert p.governance.approval_state == "approved"


def test_forbidden_transition_blocked(fx):
    g = goals(fx)[0]
    p = _fresh_plan(fx.plans, g)
    with pytest.raises(PlanLifecycleError):
        fx.plans.transition(p, PlanLifecycleState.READY, approved=True)  # PROPOSED->READY illegal


def test_cannot_ready_without_approval():
    from _v4_helpers import build_v4
    base = build_v4(1)
    g = goals_for(base)[0]
    svc = PlanService(lineage_tracker=base.tracker)   # no decider -> needs approved=True
    p = _fresh_plan(svc, g)
    svc.transition(p, PlanLifecycleState.DRAFT)
    svc.transition(p, PlanLifecycleState.UNDER_REVIEW)
    with pytest.raises(PlanGovernanceError):
        svc.transition(p, PlanLifecycleState.APPROVED, approved=False)


def test_suspend_and_resume():
    from _v4_helpers import build_v4
    base = build_v4(1)
    g = goals_for(base)[0]
    svc = PlanService(lineage_tracker=base.tracker)
    p = _fresh_plan(svc, g)
    for st in (PlanLifecycleState.DRAFT, PlanLifecycleState.UNDER_REVIEW,
               PlanLifecycleState.APPROVED, PlanLifecycleState.READY):
        svc.transition(p, st, approved=True)
    svc.transition(p, PlanLifecycleState.SUSPENDED, approved=True)
    assert p.state == PlanLifecycleState.SUSPENDED
    svc.transition(p, PlanLifecycleState.READY, approved=True)
    assert p.state == PlanLifecycleState.READY


# --- dependencies -------------------------------------------------------------
def test_plan_dependencies_are_versioned_and_traceable(fx):
    p = plans(fx)[0]
    deps = fx.plans.registry.dependencies_for(p.plan_id)
    assert deps
    for d in deps:
        assert d.version and d.dependency_id.startswith("planrel+")
        assert d.source_plan_id == p.plan_id


def test_dependency_cycle_detection():
    a = PlanDependency(dependency_id="planrel+" + "1" * 16, source_plan_id="plan+" + "a" * 16,
                       relation="depends_on", target_id="plan+" + "b" * 16, target_kind="plan")
    b = PlanDependency(dependency_id="planrel+" + "2" * 16, source_plan_id="plan+" + "b" * 16,
                       relation="depends_on", target_id="plan+" + "a" * 16, target_kind="plan")
    assert has_cycle([a, b]) is True
    assert has_cycle([a]) is False


def test_relate_rejects_unknown_relation(fx):
    p = plans(fx)[0]
    with pytest.raises(Exception):
        fx.plans.relate(p, relation="not_a_relation", target_id="x", target_kind="plan")


# --- governance ---------------------------------------------------------------
def test_ready_plan_is_policy_governed(fx):
    for p in plans(fx):
        assert p.governance.policy_references
        assert any(e["decision"] in ("permitted", "conditional_approval", "approved")
                   for e in p.governance.approval_history)


# --- lineage ------------------------------------------------------------------
def test_plan_lineage_traces_to_patient(fx):
    for p in plans(fx):
        kinds = {r.kind for r in fx.tracker.chain(p.lineage_id)}
        assert {"plan", "goal", "analytics", "workflow", "event", "case", "patient"} <= kinds
        assert fx.tracker.verify_chain(p.lineage_id)


# --- validation ---------------------------------------------------------------
def test_full_plan_validation_passes(fx):
    for p in plans(fx):
        rep = fx.plans.validate(p).to_dict()
        names = {c["name"] for c in rep["checks"]}
        assert {"identity_integrity", "lifecycle_integrity", "registry_integrity",
                "dependency_integrity", "governance_integrity", "audit_integrity",
                "lineage_integrity", "version_integrity"} <= names
        assert rep["ok"], rep


def test_plan_audit_verifies(fx):
    assert fx.plans.audit.verify()
    assert len(fx.plans.audit) > 0


def test_plans_are_reproducible():
    a = build_v4b(2)
    b = build_v4b(2)
    a_sigs = sorted(p.state_signature() for p in plans(a))
    b_sigs = sorted(p.state_signature() for p in plans(b))
    assert a_sigs == b_sigs


def test_reports_generate(fx):
    reports = fx.plans.reports(plans(fx))
    assert reports["plan_summary_report"]["n_plans"] == len(plans(fx))
    assert reports["plan_dependency_report"]["summary"]["has_cycle"] is False
    assert reports["plan_audit_report"]["verified"]


def goals_for(base):
    from _v4_helpers import goals as _g
    return _g(base)
