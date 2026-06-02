"""Tests for the Task Intelligence Layer (V4-P4).

Covers the task taxonomy, registry, lifecycle (legal + forbidden transitions, incl.
BLOCKED/unblock), dependencies (versioned + acyclic), governance, plan->task
derivation, lineage to the patient, validation (8 dimensions), determinism, and
audit immutability.
"""

from __future__ import annotations

import pytest

from backend.task_intelligence import (
    TaskService, TaskMetadata, TaskCategory, TaskPriority, TaskLifecycleState,
    TaskLifecycleError, TaskGovernanceError, TaskDerivationError, TaskRegistry,
    mint_task, validate_identity, is_category, ancestry, has_cycle, TASK_CATEGORIES,
)
from backend.task_intelligence.models import TaskRegistryRecord, TaskDependency

from _v4b_helpers import build_v4b, plans, tasks


@pytest.fixture(scope="module")
def fx():
    return build_v4b(2)


def _fresh_task(svc, plan):
    return svc.create_task(category=TaskCategory.WORKFLOW, task_key="k",
                           metadata=TaskMetadata(title="T", work_definition="w"),
                           source_plan_id=plan.plan_id, source_plan_lineage_id=plan.lineage_id,
                           source_plan_state=plan.state.value, source_goal_id=plan.source_goal_id,
                           priority=TaskPriority.MEDIUM)


# --- taxonomy -----------------------------------------------------------------
def test_task_taxonomy_is_hierarchical():
    assert is_category(TaskCategory.WORKFLOW)
    chain = ancestry(TaskCategory.VALIDATION)
    assert chain[-1] == TaskCategory.OPERATIONAL       # apex
    assert len(TASK_CATEGORIES) >= 8


# --- identity -----------------------------------------------------------------
def test_task_identity_is_deterministic():
    a = mint_task("workflow", "plan+" + "a" * 16, "reorder")
    b = mint_task("workflow", "plan+" + "a" * 16, "reorder")
    assert a.id == b.id and validate_identity(a.id)[0]


# --- registry -----------------------------------------------------------------
def test_no_task_outside_registry(fx):
    for t in tasks(fx):
        assert fx.tasks.registry.exists(t.task_id)
        assert fx.tasks.registry.get(t.task_id).version == t.version


def test_registry_rejects_silent_overwrite():
    reg = TaskRegistry()
    rec = TaskRegistryRecord(task_id="task+" + "a" * 16, category="workflow",
                             source_plan_id="plan+" + "c" * 16, state="proposed", priority="high",
                             version="v1", approval_state="pending", dependencies=(),
                             plan_references=(), goal_references=(), policy_references=(),
                             lineage_id="lineage+" + "b" * 16, audit_state="h",
                             content_signature_value="sig-1")
    reg.register(rec)
    bad = TaskRegistryRecord(task_id="task+" + "a" * 16, category="workflow",
                             source_plan_id="plan+" + "c" * 16, state="proposed", priority="high",
                             version="v1", approval_state="pending", dependencies=(),
                             plan_references=(), goal_references=(), policy_references=(),
                             lineage_id="lineage+" + "b" * 16, audit_state="h",
                             content_signature_value="sig-2")
    with pytest.raises(ValueError):
        reg.register(bad)


# --- plan -> task integration -------------------------------------------------
def test_every_task_derives_from_a_plan(fx):
    plan_ids = {p.plan_id for p in plans(fx)}
    for t in tasks(fx):
        assert t.source_plan_id in plan_ids


def test_cannot_derive_task_from_unready_plan(fx):
    # a fresh plan that is only PROPOSED (not READY)
    p = plans(fx)[0]
    svc = TaskService(lineage_tracker=fx.tracker)
    with pytest.raises(TaskDerivationError):
        svc.create_task(category=TaskCategory.WORKFLOW, task_key="x",
                        metadata=TaskMetadata(title="T", work_definition="w"),
                        source_plan_id="plan+" + "f" * 16, source_plan_lineage_id=p.lineage_id,
                        source_plan_state="proposed")


# --- lifecycle ----------------------------------------------------------------
def test_task_lifecycle_reaches_ready(fx):
    for t in tasks(fx):
        assert t.state == TaskLifecycleState.READY
        assert t.governance.approval_state == "approved"


def test_forbidden_transition_blocked(fx):
    p = plans(fx)[0]
    t = _fresh_task(fx.tasks, p)
    with pytest.raises(TaskLifecycleError):
        fx.tasks.transition(t, TaskLifecycleState.READY, approved=True)  # PROPOSED->READY illegal


def test_block_and_unblock(fx):
    p = plans(fx)[0]
    svc = TaskService(lineage_tracker=fx.tracker)
    t = _fresh_task(svc, p)
    for st in (TaskLifecycleState.DRAFT, TaskLifecycleState.UNDER_REVIEW,
               TaskLifecycleState.APPROVED, TaskLifecycleState.READY):
        svc.transition(t, st, approved=True)
    svc.transition(t, TaskLifecycleState.BLOCKED, reason="waiting dep")   # not governed
    assert t.state == TaskLifecycleState.BLOCKED
    svc.transition(t, TaskLifecycleState.READY, approved=True)
    assert t.state == TaskLifecycleState.READY


def test_cannot_ready_without_approval(fx):
    p = plans(fx)[0]
    svc = TaskService(lineage_tracker=fx.tracker)   # no decider -> needs approved=True
    t = _fresh_task(svc, p)
    svc.transition(t, TaskLifecycleState.DRAFT)
    svc.transition(t, TaskLifecycleState.UNDER_REVIEW)
    svc.transition(t, TaskLifecycleState.APPROVED, approved=True)
    with pytest.raises(TaskGovernanceError):
        svc.transition(t, TaskLifecycleState.READY, approved=False)


# --- dependencies -------------------------------------------------------------
def test_task_dependencies_are_versioned_and_traceable(fx):
    t = tasks(fx)[0]
    deps = fx.tasks.registry.dependencies_for(t.task_id)
    assert deps
    for d in deps:
        assert d.version and d.dependency_id.startswith("taskrel+")
        assert d.source_task_id == t.task_id


def test_dependency_cycle_detection():
    a = TaskDependency(dependency_id="taskrel+" + "1" * 16, source_task_id="task+" + "a" * 16,
                       relation="depends_on", target_id="task+" + "b" * 16, target_kind="task")
    b = TaskDependency(dependency_id="taskrel+" + "2" * 16, source_task_id="task+" + "b" * 16,
                       relation="depends_on", target_id="task+" + "a" * 16, target_kind="task")
    assert has_cycle([a, b]) is True
    assert has_cycle([a]) is False


# --- governance ---------------------------------------------------------------
def test_ready_task_is_policy_governed(fx):
    for t in tasks(fx):
        assert t.governance.policy_references
        assert any(e["decision"] in ("permitted", "conditional_approval", "approved")
                   for e in t.governance.approval_history)


# --- lineage ------------------------------------------------------------------
def test_task_lineage_traces_to_patient(fx):
    for t in tasks(fx):
        kinds = {r.kind for r in fx.tracker.chain(t.lineage_id)}
        assert {"task", "plan", "goal", "analytics", "workflow", "event", "case",
                "patient"} <= kinds
        assert fx.tracker.verify_chain(t.lineage_id)


# --- validation ---------------------------------------------------------------
def test_full_task_validation_passes(fx):
    for t in tasks(fx):
        rep = fx.tasks.validate(t).to_dict()
        names = {c["name"] for c in rep["checks"]}
        assert {"identity_integrity", "lifecycle_integrity", "registry_integrity",
                "dependency_integrity", "governance_integrity", "audit_integrity",
                "lineage_integrity", "version_integrity"} <= names
        assert rep["ok"], rep


def test_task_audit_verifies(fx):
    assert fx.tasks.audit.verify()
    assert len(fx.tasks.audit) > 0


def test_tasks_are_reproducible():
    a = build_v4b(2)
    b = build_v4b(2)
    a_sigs = sorted(t.state_signature() for t in tasks(a))
    b_sigs = sorted(t.state_signature() for t in tasks(b))
    assert a_sigs == b_sigs


def test_reports_generate(fx):
    reports = fx.tasks.reports(tasks(fx))
    assert reports["task_summary_report"]["n_tasks"] == len(tasks(fx))
    assert reports["task_dependency_report"]["summary"]["has_cycle"] is False
    assert reports["task_audit_report"]["verified"]
