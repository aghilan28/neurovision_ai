"""Tests for the Simulation & Scenario Layer (V4-P9).

Verifies the simulation environment is deterministic, explainable, traceable, audited,
governed, and **evaluate-only** (it never executes/authorizes/mutates). Uses the shared
V4-P9 fixture (`build_v4e`) over the one platform lineage tracker.
"""

from __future__ import annotations

import re

import pytest

from _v4e_helpers import build_v4e, baseline

from backend.simulation_scenario import (
    SimulationGate, SimulationGovernanceError, SCENARIO_TYPES, SIM_DIMENSIONS, FORECAST_TYPES, SIM_RISK_DIMENSIONS,
    OutcomeStatus,
)
from backend.simulation_scenario.schemas import all_contracts, validate_entity


@pytest.fixture(scope="module")
def fx():
    return build_v4e(2)


@pytest.fixture(scope="module")
def svc(fx):
    return fx.simulation


@pytest.fixture(scope="module")
def base_pair(svc):
    return baseline(svc, "execution")


# --- 1. scenario engine -------------------------------------------------------
def test_scenario_engine_all_types(svc):
    for stype in SCENARIO_TYPES:
        sc = svc.create_scenario(scenario_type=stype, name=f"{stype}-s")
        assert re.match(r"^scenario\+[0-9a-f]{16}$", sc.scenario_id)
        assert sc.scenario_type == stype
        assert sc.context.signature()  # reproducible content-addressed context


def test_scenario_is_reproducible(svc):
    a = svc.create_scenario(scenario_type="goal", name="repro")
    b = svc.create_scenario(scenario_type="goal", name="repro")
    assert a.scenario_id == b.scenario_id


# --- 2. simulation engine -----------------------------------------------------
def test_simulation_engine_deterministic_outcomes(base_pair):
    scenario, sim = base_pair
    assert re.match(r"^sim\+[0-9a-f]{16}$", sim.simulation_id)
    dims = {o.dimension for o in sim.result.outcomes}
    assert set(SIM_DIMENSIONS) <= dims
    assert all(o.status in (OutcomeStatus.READY, OutcomeStatus.DEGRADED, OutcomeStatus.BLOCKED)
               for o in sim.result.outcomes)
    assert 0.0 <= sim.result.readiness_score <= 1.0


# --- 3. forecast layer --------------------------------------------------------
def test_forecast_layer_explainable(base_pair):
    _, sim = base_pair
    types = {f.forecast_type for f in sim.result.forecasts}
    assert set(FORECAST_TYPES) <= types
    assert all(0.0 <= f.confidence <= 1.0 and f.factors and f.explanation
               for f in sim.result.forecasts)


# --- 4. comparison engine -----------------------------------------------------
def test_comparison_engine(svc, fx):
    a_s, a_sim = baseline(svc, "execution")
    aid = __import__("_v4c_helpers", fromlist=["agents"]).agents(fx.base.base)[0].agent_id
    b_s = svc.create_scenario(scenario_type="execution", name="exclude-agent",
                              assumptions={"exclude_agents": [aid]})
    b_sim = svc.simulate(b_s)
    cmp = svc.compare([(a_s, a_sim), (b_s, b_sim)])
    assert re.match(r"^simcmp\+[0-9a-f]{16}$", cmp.comparison_id)
    assert cmp.recommended_scenario_id in cmp.scenario_ids
    # baseline (no exclusion) should be at least as ready as the excluded scenario
    assert a_sim.result.readiness_score >= b_sim.result.readiness_score
    assert cmp.tradeoffs and cmp.governance_impact and cmp.constraint_impact


# --- 5. simulation risk engine ------------------------------------------------
def test_risk_engine_explainable_bounded(base_pair):
    _, sim = base_pair
    dims = {r.dimension for r in sim.result.risks}
    assert SIM_RISK_DIMENSIONS <= dims
    assert all(0.0 <= r.score <= 1.0 and r.factors and r.explanation for r in sim.result.risks)


# --- 6. simulation registry ---------------------------------------------------
def test_registry_tracks_artifacts(svc, base_pair):
    scenario, sim = base_pair
    assert svc.registry.exists(scenario.scenario_id)
    assert svc.registry.exists(sim.simulation_id)
    assert sim.simulation_id in svc.registry.list_simulations()
    assert svc.registry.list_forecasts() and svc.registry.list_risks()


# --- 7. simulation lineage (reaches patient + full spine) ---------------------
def test_lineage_reaches_patient_and_spine(fx, base_pair):
    _, sim = base_pair
    assert fx.tracker.verify_chain(sim.lineage_id)
    kinds = {r.kind for r in fx.tracker.chain(sim.lineage_id)}
    assert {"patient", "goal", "policy", "plan", "task", "agent", "execution",
            "governance_intelligence", "scenario", "simulation"} <= kinds


# --- 8. simulation validation -------------------------------------------------
def test_validation_all_dimensions(svc, base_pair):
    scenario, sim = base_pair
    report = svc.validate(simulation=sim, scenario=scenario)
    assert report.ok
    names = {c.name for c in report.checks}
    assert {"scenario_integrity", "simulation_integrity", "forecast_integrity",
            "comparison_integrity", "registry_integrity", "audit_integrity",
            "lineage_integrity", "version_integrity"} <= names


# --- 9-12. reports ------------------------------------------------------------
def test_reports(svc, fx):
    a_s, a_sim = baseline(svc, "plan")
    b_s, b_sim = baseline(svc, "task")
    cmp = svc.compare([(a_s, a_sim), (b_s, b_sim)])
    reports = svc.reports(scenario=a_s, simulation=a_sim, comparison=cmp)
    for key in ("scenario_report", "simulation_report", "forecast_report", "risk_report",
                "comparison_report", "simulation_audit_report", "simulation_lineage_report"):
        assert key in reports
    assert reports["simulation_audit_report"]["verified"]
    assert reports["simulation_lineage_report"]["lineage_verified"]


# --- determinism --------------------------------------------------------------
def test_simulation_is_deterministic():
    s1, sim1 = baseline(build_v4e(2).simulation, "execution")
    s2, sim2 = baseline(build_v4e(2).simulation, "execution")
    assert s1.scenario_id == s2.scenario_id
    assert sim1.simulation_id == sim2.simulation_id
    assert sim1.result.readiness_score == sim2.result.readiness_score
    assert sim1.state_signature() == sim2.state_signature()


# --- audit --------------------------------------------------------------------
def test_audit_chain_verifies(svc):
    assert svc.audit.verify()


# --- evaluate-only invariant --------------------------------------------------
def test_simulation_does_not_mutate_production():
    """Running a simulation must not change any observed entity's state."""
    fx = build_v4e(2)
    from _v4c_helpers import executions as _execs
    before = [(e.execution_id, e.state.value, e.governance.authorization_state)
              for e in _execs(fx.base.base)]
    baseline(fx.simulation, "execution")
    baseline(fx.simulation, "governance")
    after = [(e.execution_id, e.state.value, e.governance.authorization_state)
             for e in _execs(fx.base.base)]
    assert before == after


def test_gate_rejects_action_claim(svc, base_pair):
    """The gate must reject a simulation whose outcome claims a real action occurred."""
    from dataclasses import replace
    from backend.simulation_scenario.models.domain import SimulationOutcome
    scenario, sim = base_pair
    tampered_outcomes = (SimulationOutcome(dimension="execution_structures",
                                           status="executed", score=1.0, detail="x",
                                           metrics={}),) + sim.result.outcomes[1:]
    bad_result = replace(sim.result, outcomes=tampered_outcomes)
    bad_sim = replace(sim, result=bad_result)
    gate = SimulationGate()
    report = gate.evaluate_simulation(simulation=bad_sim, parents=("lineage+0" * 1,),
                                      requires_lineage=False)
    assert not report.ok
    with pytest.raises(SimulationGovernanceError):
        gate.raise_if_failed(report)


# --- contracts ----------------------------------------------------------------
def test_entity_contracts(svc):
    contracts = all_contracts()["contracts"]
    for name in ("ScenarioRecord", "SimulationRecord", "SimulationResult", "ForecastRecord",
                 "ComparisonRecord", "SimulationRiskRecord", "ScenarioContext"):
        assert name in contracts
    ok, missing = validate_entity("ForecastRecord",
                                  {"forecast_id": "x", "forecast_type": "risk_forecast",
                                   "projected_status": "low_risk", "confidence": 0.5})
    assert ok and not missing
