"""End-to-end: V4-P9 Simulation & Scenario Layer + V4-P10 Version 4 Certification.

Asserts the full deliverable chain executes with complete traceability:

    Patient -> ... -> Goal -> Policy -> Constraint -> Plan -> Task -> Agent ->
    Execution -> Governance Intelligence -> Human Oversight -> Simulation -> Certification

over the one shared lineage tracker, that prior-version integrity remains intact, and
that the V4-P10 certification document set is present and substantive.
"""

from __future__ import annotations

import pathlib

import pytest

from _v4e_helpers import build_v4e, baseline
from _v4c_helpers import goals, plans, tasks, agents, executions

REPO = pathlib.Path(__file__).resolve().parents[1]
CERT_DIR = REPO / "docs" / "certification" / "v4"
CERT_DOCS = [
    "V4_CERTIFICATION_STANDARD.md", "V4_READINESS_ASSESSMENT.md", "V4_AUDIT_FRAMEWORK.md",
    "V4_RISK_REVIEW.md", "V4_GAP_ANALYSIS.md", "V4_EXIT_CRITERIA.md",
    "V4_COMPLETION_REPORT.md", "V5_READINESS_GATE.md",
]


@pytest.fixture(scope="module")
def fx():
    return build_v4e(2)


def test_full_deliverable_chain_traceable(fx):
    """A single verify_chain spans Patient -> ... -> Governance Intelligence -> Simulation."""
    scenario, sim = baseline(fx.simulation, "execution")
    assert fx.tracker.verify_chain(sim.lineage_id)
    kinds = {r.kind for r in fx.tracker.chain(sim.lineage_id)}
    spine = {"patient", "case", "review", "finding", "event", "workflow", "analytics",
             "recommendation", "goal", "policy", "plan", "task", "agent",
             "agent_assignment", "execution", "governance_intelligence", "scenario",
             "simulation"}
    assert spine <= kinds, sorted(spine - kinds)


def test_simulation_evaluates_not_executes(fx):
    scenario, sim = baseline(fx.simulation, "execution")
    # readiness in [0,1]; forecasts are projections (would_*/low_risk/...), never "executed"
    assert 0.0 <= sim.result.readiness_score <= 1.0
    for f in sim.result.forecasts:
        assert f.projected_status not in ("executed", "authorized", "committed", "deployed")
    assert fx.simulation.validate(simulation=sim, scenario=scenario).ok


def test_prior_version_integrity_intact(fx):
    base = fx.base.base          # V4cFixture
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
    # audits across every subsystem still verify (incl. governance intelligence + simulation)
    assert gs.audit.verify() and ps.audit.verify() and plan_svc.audit.verify()
    assert task_svc.audit.verify() and base.agents.audit.verify()
    assert base.executions.audit.verify()
    assert fx.base.governance.audit.verify() and fx.simulation.audit.verify()


def test_governance_intelligence_still_valid(fx):
    gi = fx.base.governance
    rec = fx.base.intelligence
    assert gi.validate(rec).ok
    assert rec.violations == ()


# --- V4-P10 certification document set ----------------------------------------
def test_certification_docs_present():
    assert CERT_DIR.is_dir()
    for name in CERT_DOCS:
        path = CERT_DIR / name
        assert path.is_file(), f"missing certification doc {name}"
        assert len(path.read_text(encoding="utf-8")) > 400, f"{name} too thin"


def test_readiness_assessment_is_measurable():
    text = (CERT_DIR / "V4_READINESS_ASSESSMENT.md").read_text(encoding="utf-8")
    assert "Readiness" in text and "threshold" in text.lower()
    for dim in ("Goal Readiness", "Simulation Readiness", "Version Readiness"):
        assert dim in text


def test_exit_criteria_and_v5_gate_defined():
    exit_text = (CERT_DIR / "V4_EXIT_CRITERIA.md").read_text(encoding="utf-8")
    assert "EC-1" in exit_text and "EC-18" in exit_text
    gate_text = (CERT_DIR / "V5_READINESS_GATE.md").read_text(encoding="utf-8")
    assert "Forbidden shortcuts" in gate_text or "Forbidden" in gate_text
    assert "G1" in gate_text and "DENIED" in gate_text


def test_completion_report_outcome_is_evidence_bound():
    text = (CERT_DIR / "V4_COMPLETION_REPORT.md").read_text(encoding="utf-8")
    # the outcome must cite the executable judge, not self-attest
    assert "verify_v4_p9_p10" in text
    assert "CERTIFIED" in text
