"""End-to-end: V4-P7 Governance Intelligence + V4-P8 Human Oversight Workstation.

Asserts the full deliverable chain executes with complete traceability:

    Patient -> Case -> Review -> Finding -> Knowledge -> Decision -> Event ->
    Timeline -> Workflow -> Graph -> Analytics -> Recommendations -> Goal -> Policy ->
    Constraint -> Plan -> Task -> Agent -> Execution -> Governance Intelligence ->
    Human Oversight

over the one shared platform lineage tracker, and that prior-version integrity
(goal/policy/plan/task/agent/execution lineage + audit) remains intact.
"""

from __future__ import annotations

import pytest

from _v4d_helpers import build_v4d, build_aow_snapshot
from _v4c_helpers import goals, plans, tasks, agents, executions

from frontend.autonomous_operations_workstation import build_from_snapshot


@pytest.fixture(scope="module")
def fx():
    return build_v4d(2)


def test_governance_intelligence_observes_full_v4(fx):
    rec = fx.intelligence
    for kind in ("goal", "policy", "plan", "task", "agent", "execution"):
        assert kind in rec.observed_kinds
    assert rec.n_observed == len(rec.approvals)


def test_chain_reaches_patient_and_human_oversight(fx):
    """A single verify_chain spans Patient -> ... -> Governance Intelligence."""
    rec = fx.intelligence
    tracker = fx.tracker
    assert tracker.verify_chain(rec.lineage_id)
    kinds = {r.kind for r in tracker.chain(rec.lineage_id)}
    spine = {"patient", "case", "review", "finding", "event", "workflow", "analytics",
             "recommendation", "goal", "policy", "plan", "task", "agent",
             "agent_assignment", "execution", "governance_intelligence"}
    assert spine <= kinds, sorted(spine - kinds)


def test_human_oversight_workstation_view(fx):
    snap = build_aow_snapshot(fx)
    view = build_from_snapshot(snap)
    vd = view.to_dict()
    # human oversight = workstation is coherent + traceable + governed controls
    assert vd["validation"]["ok"]
    assert len(vd["areas"]) == 11
    controls = vd["meta"]["controls_summary"]
    assert controls["n_controls"] >= 1 and controls["all_governed"]
    # the representative chain (anchor) verifies end-to-end
    assert snap["representative_chain"]["verified"]


def test_prior_version_integrity_intact(fx):
    """V4-P1..P6 lineage + audit remain intact (governance intelligence is observe-only)."""
    base = fx.base
    tracker = fx.tracker
    gs = base.base.base.goals
    ps = base.base.base.policies
    plan_svc = base.base.plans
    task_svc = base.base.tasks

    assert all(tracker.verify_chain(g.lineage_id) and gs.validate(g).ok for g in goals(base))
    assert all(tracker.verify_chain(p.lineage_id) and plan_svc.validate(p).ok
               for p in plans(base))
    assert all(tracker.verify_chain(t.lineage_id) and task_svc.validate(t).ok
               for t in tasks(base))
    assert all(tracker.verify_chain(a.lineage_id) and base.agents.validate(a).ok
               for a in agents(base))
    assert all(tracker.verify_chain(e.lineage_id) and base.executions.validate(e).ok
               for e in executions(base))
    # audits across every subsystem still verify
    assert gs.audit.verify() and ps.audit.verify() and plan_svc.audit.verify()
    assert task_svc.audit.verify() and base.agents.audit.verify()
    assert base.executions.audit.verify() and fx.governance.audit.verify()


def test_governance_intelligence_validation_and_health(fx):
    rec = fx.intelligence
    assert fx.governance.validate(rec).ok
    assert 0.0 <= rec.health_score <= 1.0
    # clean platform: no violations, monitoring clear
    assert rec.violations == ()
    assert fx.governance.monitoring(rec)["clear"]
