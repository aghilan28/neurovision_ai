"""Tests for the Policy & Constraint Engine (V4-P2).

Covers the policy taxonomy, the constraint engine (six constraint types), the
deterministic evaluation engine (five outcomes), the policy registry, policy
governance (no ACTIVE without approval), lineage, validation (8 dimensions),
determinism, and audit immutability.
"""

from __future__ import annotations

import pytest

from backend.policy_engine import (
    PolicyService, PolicyRule, ConstraintType, ConstraintCategory, PolicyCategory,
    PolicyLifecycleState, EvaluationOutcome, PolicyGovernanceError, PolicyRegistry,
    mint_policy, validate_identity,
)
from backend.policy_engine.models import PolicyRegistryRecord

from _v4_helpers import build_v4, active_policies


@pytest.fixture(scope="module")
def fx():
    return build_v4(2)


def _active_policy(svc, *, category=PolicyCategory.WORKFLOW, key="wf", subject="goal",
                   rules=(), constraint_ids=()):
    p = svc.create_policy(category=category, policy_key=key, title="T", description="d",
                          subject_kind=subject, rules=rules, constraint_ids=constraint_ids)
    svc.activate(p, authority="gov")
    return p


# --- taxonomy -----------------------------------------------------------------
def test_policy_taxonomy_and_identity():
    assert mint_policy("governance", "k").id.startswith("policy+")
    assert validate_identity(mint_policy("governance", "k").id)[0]


def test_unknown_category_rejected():
    svc = PolicyService()
    with pytest.raises(Exception):
        svc.create_policy(category="bogus", policy_key="k", title="T", description="d",
                          subject_kind="goal")


# --- constraint engine (six types) -------------------------------------------
def test_constraint_engine_builds_all_six_types():
    svc = PolicyService()
    for ctype in ConstraintType:
        c = svc.create_constraint(constraint_type=ctype.value,
                                  category=ConstraintCategory.GOVERNANCE, subject_kind="goal",
                                  constraint_key=f"k-{ctype.value}", explanation="x")
        assert c.constraint_id.startswith("constraint+") and c.version
        assert svc.registry.has_constraint(c.constraint_id)


# --- evaluation engine (five outcomes) ---------------------------------------
def _eval(svc, policy, context, request="act"):
    return svc.evaluate(policy, subject_kind="goal", subject_id="goal+" + "0" * 16,
                        request=request, context=context)


def test_evaluation_permitted_when_no_constraint_triggers():
    svc = PolicyService()
    p = _active_policy(svc)
    out = _eval(svc, p, context={"x": 1})
    assert out.outcome == EvaluationOutcome.PERMITTED.value
    assert out.evidence  # explainable


def test_evaluation_denied_on_forbidden():
    svc = PolicyService()
    c = svc.create_constraint(constraint_type=ConstraintType.FORBIDDEN.value,
                              category=ConstraintCategory.PROHIBITION, subject_kind="goal",
                              constraint_key="forbid",
                              rules=(PolicyRule("r", "blocked", "eq", True),))
    p = _active_policy(svc, key="forbid-pol", constraint_ids=(c.constraint_id,))
    out = _eval(svc, p, context={"blocked": True})
    assert out.outcome == EvaluationOutcome.DENIED.value
    assert out.triggered_constraints


def test_evaluation_escalated():
    svc = PolicyService()
    c = svc.create_constraint(constraint_type=ConstraintType.ESCALATED.value,
                              category=ConstraintCategory.ESCALATION, subject_kind="finding",
                              constraint_key="esc",
                              rules=(PolicyRule("r", "risk", "eq", "high"),))
    p = _active_policy(svc, category=PolicyCategory.ESCALATION, key="esc-pol",
                       subject="finding", constraint_ids=(c.constraint_id,))
    out = _eval(svc, p, context={"risk": "high"}, request="escalate")
    assert out.outcome == EvaluationOutcome.ESCALATED.value


def test_evaluation_requires_review_on_deferred():
    svc = PolicyService()
    c = svc.create_constraint(constraint_type=ConstraintType.DEFERRED.value,
                              category=ConstraintCategory.WORKFLOW, subject_kind="goal",
                              constraint_key="def", rules=())  # no rules -> always applies
    p = _active_policy(svc, key="def-pol", constraint_ids=(c.constraint_id,))
    out = _eval(svc, p, context={})
    assert out.outcome == EvaluationOutcome.REQUIRES_REVIEW.value


def test_evaluation_conditional_approval():
    svc = PolicyService()
    c = svc.create_constraint(constraint_type=ConstraintType.CONDITIONAL.value,
                              category=ConstraintCategory.QUALITY, subject_kind="goal",
                              constraint_key="cond", rules=())
    p = _active_policy(svc, key="cond-pol", constraint_ids=(c.constraint_id,))
    out = _eval(svc, p, context={})
    assert out.outcome == EvaluationOutcome.CONDITIONAL_APPROVAL.value


def test_required_unmet_denies():
    svc = PolicyService()
    c = svc.create_constraint(constraint_type=ConstraintType.REQUIRED.value,
                              category=ConstraintCategory.OBLIGATION, subject_kind="goal",
                              constraint_key="req", rules=())  # always applies
    p = _active_policy(svc, key="req-pol", constraint_ids=(c.constraint_id,))
    # requirement not satisfied -> denied
    assert _eval(svc, p, context={"req_satisfied": False}).outcome == \
        EvaluationOutcome.DENIED.value
    # requirement satisfied -> permitted
    assert _eval(svc, p, context={"req_satisfied": True}).outcome == \
        EvaluationOutcome.PERMITTED.value


def test_evaluation_is_deterministic_and_explainable():
    svc = PolicyService()
    p = _active_policy(svc)
    a = _eval(svc, p, context={"x": 1})
    b = _eval(svc, p, context={"x": 1})
    assert a.evaluation_id == b.evaluation_id        # same policy + request -> same id
    assert a.state_signature() == b.state_signature()
    assert a.applied_rules == b.applied_rules


# --- governance (no ACTIVE without approval) ---------------------------------
def test_policy_cannot_activate_without_approval():
    svc = PolicyService()
    p = svc.create_policy(category=PolicyCategory.GOVERNANCE, policy_key="g", title="T",
                          description="d", subject_kind="goal")
    svc.transition(p, PolicyLifecycleState.UNDER_REVIEW)
    with pytest.raises(PolicyGovernanceError):
        svc.transition(p, PolicyLifecycleState.APPROVED, approved=False)


def test_inactive_policy_cannot_evaluate():
    svc = PolicyService()
    p = svc.create_policy(category=PolicyCategory.GOVERNANCE, policy_key="g2", title="T",
                          description="d", subject_kind="goal")
    with pytest.raises(PolicyGovernanceError):
        _eval(svc, p, context={})


# --- registry -----------------------------------------------------------------
def test_no_policy_outside_registry(fx):
    for pid in fx.policies.registry.list_policies():
        assert fx.policies.registry.exists(pid)


def test_registry_rejects_silent_overwrite():
    reg = PolicyRegistry()
    rec = PolicyRegistryRecord(policy_id="policy+" + "a" * 16, category="governance",
                               subject_kind="goal", state="active", approval_state="approved",
                               version="v1", constraint_ids=(), lineage_id="lineage+" + "b" * 16,
                               audit_state="h", content_signature_value="s1")
    reg.register(rec)
    bad = PolicyRegistryRecord(policy_id="policy+" + "a" * 16, category="governance",
                               subject_kind="goal", state="active", approval_state="approved",
                               version="v1", constraint_ids=(), lineage_id="lineage+" + "b" * 16,
                               audit_state="h", content_signature_value="s2")
    with pytest.raises(ValueError):
        reg.register(bad)


# --- lineage / validation -----------------------------------------------------
def test_policy_and_evaluation_lineage_verify(fx):
    for p in active_policies(fx):
        assert fx.tracker.verify_chain(p.lineage_id)
    for eid in fx.policies.registry.list_evaluations():
        ev = fx.policies.registry.evaluation(eid)
        assert fx.tracker.verify_chain(ev.lineage_id)


def test_full_policy_validation_passes(fx):
    for p in active_policies(fx):
        rep = fx.policies.validate(p).to_dict()
        names = {c["name"] for c in rep["checks"]}
        assert {"policy_integrity", "constraint_integrity", "evaluation_integrity",
                "registry_integrity", "governance_integrity", "audit_integrity",
                "lineage_integrity", "version_integrity"} <= names
        assert rep["ok"], rep


def test_policy_audit_verifies(fx):
    assert fx.policies.audit.verify()


def test_reports_generate(fx):
    reports = fx.policies.reports(active_policies(fx))
    assert reports["constraint_report"]["n_constraints"] >= 4
    assert reports["evaluation_report"]["n_evaluations"] >= 1
    assert reports["policy_audit_report"]["verified"]
