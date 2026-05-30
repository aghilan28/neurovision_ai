"""Tests for the Execution Orchestration Layer (V4-P6).

Covers the execution lifecycle (legal + forbidden transitions, incl. pause/block),
authorization gating (ACTIVE requires authorization), coordination (references an
approved assignment; progressable assignment), monitoring (read-only status; never
modifies), registry, governance, lineage to the patient, validation (9 dimensions),
determinism, and audit immutability.
"""

from __future__ import annotations

import pytest

from backend.execution_orchestration import (
    ExecutionService, ExecutionMetadata, ExecutionContext, ExecutionAssignment,
    ExecutionLifecycleState, ExecutionLifecycleError, ExecutionGovernanceError,
    ExecutionCoordinationError, ExecutionRegistry, mint_execution, validate_identity, observe,
)
from backend.execution_orchestration.models import ExecutionRegistryRecord

from _v4c_helpers import build_v4c, executions, tasks


@pytest.fixture(scope="module")
def fx():
    return build_v4c(2)


def _fresh_execution(fx, *, assignment_state="assigned"):
    """A standalone execution referencing the first task's approved assignment."""
    task = tasks(fx)[0]
    asn = fx.assignments[task.task_id]
    ctx = ExecutionContext(goal_id=task.source_goal_id, plan_id=task.source_plan_id,
                           task_id=task.task_id, agent_id=asn.agent_id,
                           assignment_id=asn.assignment_id)
    easn = ExecutionAssignment(assignment_id=asn.assignment_id, agent_id=asn.agent_id,
                               task_id=task.task_id, assignment_state=assignment_state)
    svc = ExecutionService(lineage_tracker=fx.tracker)
    return svc, svc.create_execution(execution_key="standalone",
                                     metadata=ExecutionMetadata(title="T", objective="o"),
                                     context=ctx, assignment=easn,
                                     assignment_lineage_id=asn.lineage_id)


# --- identity -----------------------------------------------------------------
def test_execution_identity_is_deterministic():
    a = mint_execution("task+" + "c" * 16, "agentassign+" + "e" * 16, "run")
    b = mint_execution("task+" + "c" * 16, "agentassign+" + "e" * 16, "run")
    assert a.id == b.id and validate_identity(a.id)[0]


# --- registry -----------------------------------------------------------------
def test_no_execution_outside_registry(fx):
    for e in executions(fx):
        assert fx.executions.registry.exists(e.execution_id)
        assert fx.executions.registry.get(e.execution_id).version == e.version


def test_registry_rejects_silent_overwrite():
    reg = ExecutionRegistry()
    rec = ExecutionRegistryRecord(execution_id="execution+" + "a" * 16,
                                  source_task_id="task+" + "c" * 16,
                                  assignment_id="agentassign+" + "e" * 16, state="proposed",
                                  version="v1", authorization_state="pending",
                                  agent_references=(), task_references=(), policy_references=(),
                                  lineage_id="lineage+" + "b" * 16, audit_state="h",
                                  content_signature_value="s1")
    reg.register(rec)
    bad = ExecutionRegistryRecord(execution_id="execution+" + "a" * 16,
                                  source_task_id="task+" + "c" * 16,
                                  assignment_id="agentassign+" + "e" * 16, state="proposed",
                                  version="v1", authorization_state="pending",
                                  agent_references=(), task_references=(), policy_references=(),
                                  lineage_id="lineage+" + "b" * 16, audit_state="h",
                                  content_signature_value="s2")
    with pytest.raises(ValueError):
        reg.register(bad)


# --- coordination -------------------------------------------------------------
def test_every_execution_references_an_assignment(fx):
    for e in executions(fx):
        assert e.assignment_id and e.context.task_id and e.context.agent_id


def test_incomplete_context_rejected(fx):
    svc = ExecutionService(lineage_tracker=fx.tracker)
    ctx = ExecutionContext(task_id="", agent_id="agent+" + "d" * 16,
                           assignment_id="agentassign+" + "e" * 16)  # missing task
    easn = ExecutionAssignment(assignment_id="agentassign+" + "e" * 16,
                               agent_id="agent+" + "d" * 16, task_id="task+" + "c" * 16,
                               assignment_state="assigned")
    with pytest.raises(ExecutionCoordinationError):
        svc.create_execution(execution_key="x", metadata=ExecutionMetadata(title="T", objective="o"),
                             context=ctx, assignment=easn, assignment_lineage_id=None)


def test_non_progressable_assignment_rejected(fx):
    with pytest.raises(ExecutionCoordinationError):
        _fresh_execution(fx, assignment_state="revoked")


# --- lifecycle + authorization ------------------------------------------------
def test_execution_lifecycle_reaches_completed(fx):
    for e in executions(fx):
        assert e.state == ExecutionLifecycleState.COMPLETED
        assert e.governance.authorization_state == "authorized"


def test_forbidden_transition_blocked(fx):
    svc, ex = _fresh_execution(fx)
    with pytest.raises(ExecutionLifecycleError):
        svc.transition(ex, ExecutionLifecycleState.ACTIVE, approved=True)  # PROPOSED->ACTIVE


def test_cannot_activate_without_authorization(fx):
    svc, ex = _fresh_execution(fx)
    svc.transition(ex, ExecutionLifecycleState.QUEUED)
    svc.transition(ex, ExecutionLifecycleState.AUTHORIZED, approved=True, authority="gov")
    with pytest.raises(ExecutionGovernanceError):
        svc.transition(ex, ExecutionLifecycleState.ACTIVE, approved=False)


def test_pause_block_resume(fx):
    svc, ex = _fresh_execution(fx)
    svc.transition(ex, ExecutionLifecycleState.QUEUED)
    svc.transition(ex, ExecutionLifecycleState.AUTHORIZED, approved=True)
    svc.transition(ex, ExecutionLifecycleState.ACTIVE, approved=True)
    svc.transition(ex, ExecutionLifecycleState.PAUSED, reason="pause")     # not governed
    assert ex.state == ExecutionLifecycleState.PAUSED
    svc.transition(ex, ExecutionLifecycleState.ACTIVE, approved=True)
    svc.transition(ex, ExecutionLifecycleState.BLOCKED, reason="dep")      # not governed
    assert ex.state == ExecutionLifecycleState.BLOCKED
    svc.transition(ex, ExecutionLifecycleState.ACTIVE, approved=True)
    assert ex.state == ExecutionLifecycleState.ACTIVE


# --- monitoring (observe; never modifies) -------------------------------------
def test_monitoring_observes_without_modifying(fx):
    e = executions(fx)[0]
    sig_before = e.state_signature()
    status = fx.executions.observe(e)
    assert status.progress == 1.0 and status.outcome == "completed"  # COMPLETED
    assert e.state_signature() == sig_before                          # unchanged


def test_blocked_status_reports_blocking_condition(fx):
    svc, ex = _fresh_execution(fx)
    svc.transition(ex, ExecutionLifecycleState.QUEUED)
    svc.transition(ex, ExecutionLifecycleState.AUTHORIZED, approved=True)
    svc.transition(ex, ExecutionLifecycleState.ACTIVE, approved=True)
    svc.transition(ex, ExecutionLifecycleState.BLOCKED, reason="dep")
    assert "execution_blocked" in observe(ex).blocking_conditions


# --- lineage ------------------------------------------------------------------
def test_execution_lineage_traces_to_patient(fx):
    for e in executions(fx):
        kinds = {r.kind for r in fx.tracker.chain(e.lineage_id)}
        assert {"execution", "agent_assignment", "agent", "task", "plan", "goal",
                "analytics", "workflow", "event", "case", "patient"} <= kinds
        assert fx.tracker.verify_chain(e.lineage_id)


# --- validation ---------------------------------------------------------------
def test_full_execution_validation_passes(fx):
    for e in executions(fx):
        rep = fx.executions.validate(e).to_dict()
        names = {c["name"] for c in rep["checks"]}
        assert {"identity_integrity", "lifecycle_integrity", "authorization_integrity",
                "assignment_integrity", "registry_integrity", "governance_integrity",
                "audit_integrity", "lineage_integrity", "version_integrity"} <= names
        assert rep["ok"], rep


def test_execution_audit_verifies(fx):
    assert fx.executions.audit.verify()
    assert len(fx.executions.audit) > 0


def test_executions_are_reproducible():
    a = build_v4c(2)
    b = build_v4c(2)
    a_sigs = sorted(x.state_signature() for x in executions(a))
    b_sigs = sorted(x.state_signature() for x in executions(b))
    assert a_sigs == b_sigs


def test_reports_generate(fx):
    reports = fx.executions.reports(executions(fx))
    assert reports["execution_summary_report"]["n_executions"] == len(executions(fx))
    assert reports["authorization_report"]["executions"]
    assert reports["monitoring_report"]["summary"]["n_executions"] == len(executions(fx))
    assert reports["execution_audit_report"]["verified"]
