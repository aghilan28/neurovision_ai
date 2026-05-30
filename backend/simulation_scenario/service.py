"""SimulationScenarioService — the governed orchestration hub for V4-P9.

Provides a governed, deterministic **evaluation** environment over the already-governed
Version 4 artifacts (goals V4-P1, policies/constraints V4-P2, plans V4-P3, tasks V4-P4,
agents V4-P5, executions V4-P6) and the V4-P7 governance intelligence. It can:

  * build reproducible **scenarios** (hypotheses) of each type,
  * run deterministic **simulations** (evaluate -> outcomes -> forecasts -> risks),
  * **compare** simulated scenarios.

Each artifact is admitted through one governed path: simulation gate (architecture/
quality/context/risk/governance) -> shared-lineage node (parented by the evaluated
artifacts' nodes; a simulation also parents its scenario; a comparison parents its
simulations) -> immutable audit event -> content-addressed version -> registry sync.
Because the lineage parents are the evaluated artifacts' nodes, ``verify_chain`` spans
Patient -> ... -> Execution -> Governance Intelligence -> Scenario -> Simulation.

The simulation layer **evaluates, never executes**: it never authorizes, commits, or
modifies production state. Shares the platform's single ``ml.lineage.LineageTracker``
and the shared ``ImmutableAuditLog`` — no parallel lineage/audit/governance.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional, Sequence

from ml.lineage import LineageTracker  # allowed: backend -> ml

from .version import DETERMINISTIC_EPOCH
from .models.domain import (
    ScenarioRecord, SimulationRecord, ComparisonRecord, SimulationVersion,
    SimulationRegistryRecord,
)
from .models.context import SimulationView
from .scenarios import build_scenario
from .simulation import run_simulation
from .comparison import build_comparison
from .governance import SimulationGate, SimulationGovernanceError
from .registry import SimulationRegistry
from .validation import SimulationValidator
from .audit import make_simulation_audit_log
from .lineage import make_simulation_lineage
from .reports import (
    build_scenario_report, build_simulation_report, build_forecast_report,
    build_comparison_report, build_risk_report, build_validation_report, build_audit_report,
    build_lineage_report,
)


def _governance_summary(governance_intelligence) -> dict:
    """Derive the governance summary the simulation needs from a V4-P7 record."""
    if governance_intelligence is None:
        return {"health_score": 1.0, "n_violations": 0, "n_high_risks": 0}
    gi = governance_intelligence
    return {"health_score": getattr(gi, "health_score", 1.0),
            "n_violations": len(getattr(gi, "violations", ())),
            "n_high_risks": getattr(gi, "n_high_risks", 0)}


class SimulationScenarioService:
    """Stateful service: simulation registry, shared lineage, immutable audit."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[SimulationRegistry] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or SimulationRegistry()
        self.audit = make_simulation_audit_log()
        self.gate = SimulationGate()
        self.validator = SimulationValidator()
        self._view: Optional[SimulationView] = None
        self._sim_lineage: dict[str, str] = {}

    # --- sources --------------------------------------------------------------
    def load_sources(self, *, goals: Sequence = (), policies: Sequence = (),
                     constraints: Sequence = (), plans: Sequence = (), tasks: Sequence = (),
                     agents: Sequence = (), executions: Sequence = (),
                     governance_intelligence=None,
                     governance_summary: dict | None = None) -> "SimulationScenarioService":
        extra_parents = ()
        if governance_intelligence is not None and getattr(governance_intelligence, "lineage_id", None):
            extra_parents = (governance_intelligence.lineage_id,)
        self._view = SimulationView.from_sources(
            goals=goals, policies=policies, constraints=constraints, plans=plans, tasks=tasks,
            agents=agents, executions=executions,
            governance_summary=governance_summary or _governance_summary(governance_intelligence),
            extra_parents=extra_parents)
        return self

    def view(self) -> SimulationView:
        if self._view is None:
            raise RuntimeError("call load_sources(...) before building scenarios")
        return self._view

    # --- scenario -------------------------------------------------------------
    def create_scenario(self, *, scenario_type: str, name: str, description: str = "",
                        assumptions: dict | None = None,
                        created_at: str = DETERMINISTIC_EPOCH) -> ScenarioRecord:
        view = self.view()
        scenario = build_scenario(view, scenario_type=scenario_type, name=name,
                                  description=description, assumptions=assumptions)
        parents = view.parents()
        report = self.gate.evaluate_scenario(scenario=scenario, parents=parents,
                                             requires_lineage=len(parents) > 0)
        self.gate.raise_if_failed(report)
        node = self.lineage.record(make_simulation_lineage(
            scenario.scenario_id, kind="scenario", parents=parents, reason="created",
            created_at=created_at))
        self.audit.append("scenario_created",
                          {"scenario_id": scenario.scenario_id, "scenario_type": scenario_type,
                           "name": name, "lineage_id": node.lineage_id}, created_at=created_at)
        scenario = replace(scenario, lineage_id=node.lineage_id, audit_state=self.audit.head)
        scenario = self._finalize(scenario, kind="scenario", artifact_id=scenario.scenario_id,
                                  reason="created", created_at=created_at)
        return scenario

    # --- simulation -----------------------------------------------------------
    def simulate(self, scenario: ScenarioRecord, *,
                 created_at: str = DETERMINISTIC_EPOCH) -> SimulationRecord:
        sim_id, result = run_simulation(scenario)
        sim = SimulationRecord(simulation_id=sim_id, scenario_id=scenario.scenario_id,
                               scenario_type=scenario.scenario_type, result=result,
                               created_at=created_at)
        parents = (scenario.lineage_id,) + tuple(scenario.context.parents) \
            if scenario.lineage_id else tuple(scenario.context.parents)
        report = self.gate.evaluate_simulation(simulation=sim, parents=parents,
                                               requires_lineage=len(parents) > 0)
        self.gate.raise_if_failed(report)
        node = self.lineage.record(make_simulation_lineage(
            sim_id, kind="simulation", parents=parents, reason="simulated", created_at=created_at))
        self.audit.append("simulation_run",
                          {"simulation_id": sim_id, "scenario_id": scenario.scenario_id,
                           "readiness": result.readiness_score, "lineage_id": node.lineage_id},
                          created_at=created_at)
        sim = replace(sim, lineage_id=node.lineage_id, audit_state=self.audit.head)
        sim = self._finalize(sim, kind="simulation", artifact_id=sim_id, reason="simulated",
                             created_at=created_at)
        self._sim_lineage[sim_id] = sim.lineage_id
        return sim

    def run(self, *, scenario_type: str, name: str, assumptions: dict | None = None,
            description: str = "") -> tuple:
        """Convenience: build a scenario and immediately simulate it."""
        scenario = self.create_scenario(scenario_type=scenario_type, name=name,
                                        description=description, assumptions=assumptions)
        return scenario, self.simulate(scenario)

    # --- comparison -----------------------------------------------------------
    def compare(self, pairs: Sequence, *, created_at: str = DETERMINISTIC_EPOCH) -> ComparisonRecord:
        comparison = build_comparison(pairs)
        parents = tuple(sim.lineage_id for _, sim in pairs if sim.lineage_id)
        report = self.gate.evaluate_comparison(comparison=comparison, parents=parents,
                                               requires_lineage=len(parents) > 0)
        self.gate.raise_if_failed(report)
        node = self.lineage.record(make_simulation_lineage(
            comparison.comparison_id, kind="simulation_comparison", parents=parents,
            reason="compared", created_at=created_at))
        self.audit.append("comparison_generated",
                          {"comparison_id": comparison.comparison_id,
                           "recommended": comparison.recommended_scenario_id,
                           "lineage_id": node.lineage_id}, created_at=created_at)
        comparison = replace(comparison, lineage_id=node.lineage_id, audit_state=self.audit.head)
        comparison = self._finalize(comparison, kind="comparison",
                                    artifact_id=comparison.comparison_id, reason="compared",
                                    created_at=created_at)
        return comparison

    # --- validation + reports -------------------------------------------------
    def validate(self, *, simulation: SimulationRecord, scenario: ScenarioRecord,
                 comparison: Optional[ComparisonRecord] = None):
        return self.validator.validate(simulation=simulation, scenario=scenario,
                                       registry=self.registry, audit_log=self.audit,
                                       lineage_tracker=self.lineage, comparison=comparison)

    def reports(self, *, scenario: ScenarioRecord, simulation: SimulationRecord,
                comparison: Optional[ComparisonRecord] = None) -> dict:
        out = {
            "scenario_report": build_scenario_report(scenario),
            "simulation_report": build_simulation_report(simulation),
            "forecast_report": build_forecast_report(simulation),
            "risk_report": build_risk_report(simulation),
            "simulation_audit_report": build_audit_report(self.audit),
            "simulation_lineage_report": build_lineage_report(simulation, self.lineage),
        }
        if comparison is not None:
            out["comparison_report"] = build_comparison_report(comparison)
        return out

    def validation_report(self, scope: str, validation_report_dict: dict) -> dict:
        return build_validation_report(scope, validation_report_dict)

    # --- internals ------------------------------------------------------------
    def _finalize(self, artifact, *, kind: str, artifact_id: str, reason: str, created_at: str):
        version = SimulationVersion.compute(artifact.state_signature(),
                                            artifact.version_previous())
        artifact = replace(artifact, version=version)
        self.audit.append("simulation_version_changed",
                          {"artifact_id": artifact_id, "artifact_kind": kind, "version": version,
                           "reason": reason}, created_at=created_at)
        artifact = replace(artifact, audit_state=self.audit.head)
        self.registry.register(SimulationRegistryRecord(
            artifact_id=artifact_id, artifact_kind=kind, version=version,
            lineage_id=artifact.lineage_id, audit_state=artifact.audit_state,
            content_signature_value=artifact.state_signature()))
        if kind == "scenario":
            self.registry.index_scenario(artifact)
        elif kind == "simulation":
            self.registry.index_simulation(artifact)
        else:
            self.registry.index_comparison(artifact)
        self.audit.append("simulation_registered",
                          {"artifact_id": artifact_id, "artifact_kind": kind, "version": version},
                          created_at=created_at)
        artifact = replace(artifact, audit_state=self.audit.head)
        return artifact


__all__ = ["SimulationScenarioService", "SimulationGovernanceError"]
