"""Tests for the Agent Coordination Framework (V4-P5).

Covers the agent taxonomy, registry, lifecycle (legal + forbidden transitions),
capability system (modes/risk/approval gating), assignment system (capability
matching + states, never implies execution), governance, lineage to the patient,
validation (9 dimensions), determinism, and audit immutability.
"""

from __future__ import annotations

import pytest

from backend.agent_coordination import (
    AgentService, AgentMetadata, AgentCapability, AgentCategory, AgentPriority,
    AgentLifecycleState, AgentLifecycleError, AgentGovernanceError, AgentCapabilityError,
    AgentRegistry, CapabilityRisk, CapabilityMode, mint_agent, validate_identity, is_category,
    ancestry, AGENT_CATEGORIES,
)
from backend.agent_coordination.models import AgentRegistryRecord

from _v4c_helpers import build_v4c, agents, tasks


@pytest.fixture(scope="module")
def fx():
    return build_v4c(2)


def _fresh_agent(svc, *, caps=(), category=AgentCategory.SYSTEM):
    return svc.create_agent(category=category, agent_key="k",
                            metadata=AgentMetadata(title="T", role="r"),
                            capabilities=caps, priority=AgentPriority.MEDIUM)


def _drive_available(svc, agent):
    for st in (AgentLifecycleState.DRAFT, AgentLifecycleState.UNDER_REVIEW,
               AgentLifecycleState.APPROVED):
        svc.transition(agent, st, approved=True)
    if svc.requires_capability_approval(agent):
        svc.approve_capabilities(agent, authority="gov")
    svc.transition(agent, AgentLifecycleState.AVAILABLE, approved=True, authority="gov")
    return agent


# --- taxonomy -----------------------------------------------------------------
def test_agent_taxonomy_is_hierarchical():
    assert is_category(AgentCategory.SERVICE)
    chain = ancestry(AgentCategory.SERVICE)
    assert chain[-1] == AgentCategory.PARTICIPANT          # apex
    assert len(AGENT_CATEGORIES) >= 8


def test_unknown_category_rejected():
    svc = AgentService()
    with pytest.raises(Exception):
        svc.create_agent(category="nope", agent_key="k",
                         metadata=AgentMetadata(title="T", role="r"))


# --- identity -----------------------------------------------------------------
def test_agent_identity_is_deterministic():
    a = mint_agent("human", "dr-x")
    b = mint_agent("human", "dr-x")
    assert a.id == b.id and validate_identity(a.id)[0]


# --- registry -----------------------------------------------------------------
def test_no_agent_outside_registry(fx):
    for a in agents(fx):
        assert fx.agents.registry.exists(a.agent_id)
        assert fx.agents.registry.get(a.agent_id).version == a.version


def test_registry_rejects_silent_overwrite():
    reg = AgentRegistry()
    rec = AgentRegistryRecord(agent_id="agent+" + "a" * 16, category="system", state="proposed",
                              priority="high", version="v1", approval_state="pending",
                              capabilities=(), assignments=(), policy_references=(),
                              lineage_id="lineage+" + "b" * 16, audit_state="h",
                              content_signature_value="s1")
    reg.register(rec)
    bad = AgentRegistryRecord(agent_id="agent+" + "a" * 16, category="system", state="proposed",
                              priority="high", version="v1", approval_state="pending",
                              capabilities=(), assignments=(), policy_references=(),
                              lineage_id="lineage+" + "b" * 16, audit_state="h",
                              content_signature_value="s2")
    with pytest.raises(ValueError):
        reg.register(bad)


# --- lifecycle ----------------------------------------------------------------
def test_agent_lifecycle_reaches_available(fx):
    for a in agents(fx):
        assert a.state == AgentLifecycleState.AVAILABLE
        assert a.governance.approval_state == "approved"


def test_forbidden_transition_blocked():
    svc = AgentService()
    a = _fresh_agent(svc)
    with pytest.raises(AgentLifecycleError):
        svc.transition(a, AgentLifecycleState.AVAILABLE, approved=True)  # PROPOSED->AVAILABLE


def test_cannot_become_available_without_approval():
    svc = AgentService()
    a = _fresh_agent(svc)
    svc.transition(a, AgentLifecycleState.DRAFT)
    svc.transition(a, AgentLifecycleState.UNDER_REVIEW)
    with pytest.raises(AgentGovernanceError):
        svc.transition(a, AgentLifecycleState.APPROVED, approved=False)


def test_suspend_and_resume():
    svc = AgentService()
    a = _drive_available(svc, _fresh_agent(svc))
    svc.transition(a, AgentLifecycleState.SUSPENDED, approved=True)
    assert a.state == AgentLifecycleState.SUSPENDED
    svc.transition(a, AgentLifecycleState.AVAILABLE, approved=True)
    assert a.state == AgentLifecycleState.AVAILABLE


# --- capability system --------------------------------------------------------
def test_high_risk_capability_blocks_availability_until_approved():
    svc = AgentService()
    caps = (AgentCapability(name="surgery", mode=CapabilityMode.ALLOWED,
                            risk=CapabilityRisk.CRITICAL),)
    a = _fresh_agent(svc, caps=caps)
    for st in (AgentLifecycleState.DRAFT, AgentLifecycleState.UNDER_REVIEW,
               AgentLifecycleState.APPROVED):
        svc.transition(a, st, approved=True)
    # high-risk capability not approved -> AVAILABLE blocked
    with pytest.raises(AgentGovernanceError):
        svc.transition(a, AgentLifecycleState.AVAILABLE, approved=True, authority="gov")
    svc.approve_capabilities(a, authority="gov")
    svc.transition(a, AgentLifecycleState.AVAILABLE, approved=True, authority="gov")
    assert a.is_available and a.governance.capability_approved


# --- assignment system --------------------------------------------------------
def test_assignment_requires_capability_match():
    svc = AgentService()
    caps = (AgentCapability(name="review", mode=CapabilityMode.ALLOWED,
                            risk=CapabilityRisk.LOW),)
    a = _drive_available(svc, _fresh_agent(svc, caps=caps))
    # satisfied
    asn = svc.assign(a, target_id="task+" + "c" * 16, target_kind="task",
                     required_capabilities=["review"])
    assert asn.state == "assigned"
    # missing capability -> rejected
    with pytest.raises(AgentCapabilityError):
        svc.assign(a, target_id="task+" + "d" * 16, target_kind="task",
                   required_capabilities=["surgery"])


def test_assignment_requires_available_agent():
    svc = AgentService()
    a = _fresh_agent(svc)  # still PROPOSED
    with pytest.raises(AgentGovernanceError):
        svc.assign(a, target_id="task+" + "c" * 16, target_kind="task")


def test_assignments_are_versioned_and_traceable(fx):
    for task in tasks(fx):
        asn = fx.assignments[task.task_id]
        assert asn.version and asn.assignment_id.startswith("agentassign+")
        assert fx.agents.registry.assignment(asn.assignment_id).state == "assigned"


def test_assignment_does_not_imply_execution(fx):
    # an assignment is a reference, not execution: no state beyond the assignment vocab
    for asn in fx.assignments.values():
        assert asn.state in ("assigned", "pending", "blocked", "revoked", "completed")
    # the agent service exposes no execute/run API
    assert not hasattr(fx.agents, "execute") and not hasattr(fx.agents, "run")


# --- governance ---------------------------------------------------------------
def test_available_agent_is_policy_governed(fx):
    for a in agents(fx):
        assert a.governance.policy_references
        assert any(e["decision"] in ("permitted", "conditional_approval", "approved")
                   for e in a.governance.approval_history)


# --- lineage ------------------------------------------------------------------
def test_agent_assignment_lineage_traces_to_patient(fx):
    # the assignment node parents the agent node + the task node -> task traces to patient
    for task in tasks(fx):
        asn = fx.assignments[task.task_id]
        kinds = {r.kind for r in fx.tracker.chain(asn.lineage_id)}
        assert {"agent_assignment", "agent", "task", "plan", "goal", "event", "case",
                "patient"} <= kinds
        assert fx.tracker.verify_chain(asn.lineage_id)


# --- validation ---------------------------------------------------------------
def test_full_agent_validation_passes(fx):
    for a in agents(fx):
        rep = fx.agents.validate(a).to_dict()
        names = {c["name"] for c in rep["checks"]}
        assert {"identity_integrity", "lifecycle_integrity", "capability_integrity",
                "assignment_integrity", "registry_integrity", "governance_integrity",
                "audit_integrity", "lineage_integrity", "version_integrity"} <= names
        assert rep["ok"], rep


def test_agent_audit_verifies(fx):
    assert fx.agents.audit.verify()
    assert len(fx.agents.audit) > 0


def test_agents_are_reproducible():
    a = build_v4c(2)
    b = build_v4c(2)
    a_sigs = sorted(x.state_signature() for x in agents(a))
    b_sigs = sorted(x.state_signature() for x in agents(b))
    assert a_sigs == b_sigs


def test_reports_generate(fx):
    reports = fx.agents.reports(agents(fx))
    assert reports["agent_summary_report"]["n_agents"] == len(agents(fx))
    assert reports["capability_report"]["agents"]
    assert reports["assignment_report"]["n_assignments"] >= len(tasks(fx))
    assert reports["agent_audit_report"]["verified"]
