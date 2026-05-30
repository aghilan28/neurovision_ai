"""Tests for the Goal Intelligence Foundation (V4-P1).

Covers the goal taxonomy, registry, lifecycle (legal + forbidden transitions),
relationships, governance, lineage-to-patient, validation (8 dimensions),
determinism, and audit immutability.
"""

from __future__ import annotations

import pytest

from backend.goal_intelligence import (
    GoalService, GoalMetadata, GoalCategory, GoalPriority, GoalLifecycleState,
    GoalLifecycleError, GoalGovernanceError, GoalRegistry, mint_goal, validate_identity,
    is_category, ancestry, GOAL_CATEGORIES,
)
from backend.goal_intelligence.models import GoalRegistryRecord

from _v4_helpers import build_v4, goals


@pytest.fixture(scope="module")
def fx():
    return build_v4(2)


# --- taxonomy -----------------------------------------------------------------
def test_goal_taxonomy_is_hierarchical():
    assert is_category(GoalCategory.WORKFLOW)
    # workflow -> operational -> strategic (apex)
    chain = ancestry(GoalCategory.WORKFLOW)
    assert chain[-1] == GoalCategory.STRATEGIC
    assert GoalCategory.OPERATIONAL in chain
    assert len(GOAL_CATEGORIES) >= 8


def test_unknown_category_rejected():
    svc = GoalService()
    with pytest.raises(Exception):
        svc.create_goal(category="not-a-category", definition_key="k",
                        metadata=GoalMetadata(title="T", desired_outcome="o"))


# --- registry -----------------------------------------------------------------
def test_no_goal_outside_registry(fx):
    for g in goals(fx):
        assert fx.goals.registry.exists(g.goal_id)
        assert fx.goals.registry.get(g.goal_id).version == g.version


def test_registry_rejects_silent_overwrite():
    reg = GoalRegistry()
    rec = GoalRegistryRecord(goal_id="goal+" + "a" * 16, category="workflow", state="proposed",
                             priority="high", version="v1", approval_state="pending",
                             dependencies=(), constraint_ids=(), lineage_id="lineage+" + "b" * 16,
                             audit_state="h", content_signature_value="sig-1")
    reg.register(rec)
    bad = GoalRegistryRecord(goal_id="goal+" + "a" * 16, category="workflow", state="proposed",
                             priority="high", version="v1", approval_state="pending",
                             dependencies=(), constraint_ids=(), lineage_id="lineage+" + "b" * 16,
                             audit_state="h", content_signature_value="sig-2")
    with pytest.raises(ValueError):
        reg.register(bad)


# --- identity -----------------------------------------------------------------
def test_goal_identity_is_deterministic():
    a = mint_goal("workflow", "reduce-latency")
    b = mint_goal("workflow", "reduce-latency")
    assert a.id == b.id and validate_identity(a.id)[0]


# --- lifecycle ----------------------------------------------------------------
def test_goal_lifecycle_reaches_active(fx):
    for g in goals(fx):
        assert g.state == GoalLifecycleState.ACTIVE
        assert g.governance.approval_state == "approved"


def test_forbidden_transition_blocked():
    svc = GoalService()
    g = svc.create_goal(category=GoalCategory.QUALITY, definition_key="dq",
                        metadata=GoalMetadata(title="DQ", desired_outcome="better"),
                        priority=GoalPriority.LOW)
    # PROPOSED -> ACTIVE is not a legal edge
    with pytest.raises(GoalLifecycleError):
        svc.transition(g, GoalLifecycleState.ACTIVE, approved=True)


def test_cannot_activate_without_approval():
    svc = GoalService()  # no policy_decider; governed transitions need approved=True
    g = svc.create_goal(category=GoalCategory.QUALITY, definition_key="dq2",
                        metadata=GoalMetadata(title="DQ", desired_outcome="better"),
                        priority=GoalPriority.LOW)
    svc.transition(g, GoalLifecycleState.DRAFT)
    svc.transition(g, GoalLifecycleState.UNDER_REVIEW)
    with pytest.raises(GoalGovernanceError):
        svc.transition(g, GoalLifecycleState.APPROVED, approved=False)


def test_suspend_and_resume():
    svc = GoalService()
    g = svc.create_goal(category=GoalCategory.OPERATIONAL, definition_key="op",
                        metadata=GoalMetadata(title="Op", desired_outcome="o"),
                        priority=GoalPriority.MEDIUM)
    for st in (GoalLifecycleState.DRAFT, GoalLifecycleState.UNDER_REVIEW,
               GoalLifecycleState.APPROVED, GoalLifecycleState.ACTIVE):
        svc.transition(g, st, approved=True)
    svc.transition(g, GoalLifecycleState.SUSPENDED, approved=True)
    assert g.state == GoalLifecycleState.SUSPENDED
    svc.transition(g, GoalLifecycleState.ACTIVE, approved=True)
    assert g.state == GoalLifecycleState.ACTIVE


# --- relationships ------------------------------------------------------------
def test_goal_relationships_are_versioned_and_traceable(fx):
    g = goals(fx)[0]
    rels = fx.goals.registry.relationships_for(g.goal_id)
    assert rels
    for r in rels:
        assert r.version and r.relationship_id.startswith("goalrel+")
        assert r.source_goal_id == g.goal_id


def test_relationship_rejects_unknown_relation(fx):
    g = goals(fx)[0]
    with pytest.raises(Exception):
        fx.goals.relate(g, relation="not_a_relation", target_id="x", target_kind="goal")


# --- governance ---------------------------------------------------------------
def test_active_goal_is_policy_governed(fx):
    for g in goals(fx):
        # the activation decision recorded a governing policy reference
        assert g.governance.policy_references
        assert any(e["decision"] in ("permitted", "conditional_approval", "approved")
                   for e in g.governance.approval_history)


# --- lineage ------------------------------------------------------------------
def test_goal_lineage_traces_to_patient(fx):
    for g in goals(fx):
        kinds = {r.kind for r in fx.tracker.chain(g.lineage_id)}
        assert {"goal", "analytics", "workflow", "event", "case", "patient"} <= kinds
        assert fx.tracker.verify_chain(g.lineage_id)


# --- validation ---------------------------------------------------------------
def test_full_goal_validation_passes(fx):
    for g in goals(fx):
        rep = fx.goals.validate(g).to_dict()
        names = {c["name"] for c in rep["checks"]}
        assert {"identity_integrity", "lifecycle_integrity", "registry_integrity",
                "relationship_integrity", "governance_integrity", "audit_integrity",
                "lineage_integrity", "version_integrity"} <= names
        assert rep["ok"], rep


def test_goal_audit_verifies(fx):
    assert fx.goals.audit.verify()
    assert len(fx.goals.audit) > 0


def test_goals_are_reproducible():
    a = build_v4(2)
    b = build_v4(2)
    a_sigs = sorted(g.state_signature() for g in goals(a))
    b_sigs = sorted(g.state_signature() for g in goals(b))
    assert a_sigs == b_sigs


def test_reports_generate(fx):
    reports = fx.goals.reports(goals(fx))
    assert reports["goal_summary_report"]["n_goals"] == len(goals(fx))
    assert reports["goal_lifecycle_report"]["goals"]
    assert reports["goal_relationship_report"]["n_relationships"] > 0
    assert reports["goal_audit_report"]["verified"]
