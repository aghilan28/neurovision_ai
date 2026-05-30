"""Simulation report builders (reproducible; version-tagged) (V4-P9).

Every report is a deterministic projection of an admitted scenario/simulation/
comparison + registry/audit/lineage state. Reports add no new truth.
"""

from __future__ import annotations

from typing import Any

from ..version import SIMULATION_REPORT_VERSION, SIMULATION_SCENARIO_VERSION
from ..forecast import forecast_summary
from ..risk import risk_summary


def _header(report_type: str, scope: str = "simulation") -> dict:
    return {"report_type": report_type, "simulation_report_version": SIMULATION_REPORT_VERSION,
            "simulation_scenario_version": SIMULATION_SCENARIO_VERSION, "scope": scope}


def build_scenario_report(scenario) -> dict:
    return {**_header("scenario", scenario.scenario_type),
            "scenario_id": scenario.scenario_id, "name": scenario.name,
            "scenario_type": scenario.scenario_type,
            "focus_kind": scenario.context.focus_kind,
            "n_observations": len(scenario.context.observations),
            "assumptions": scenario.context.assumptions_dict_parsed(),
            "lineage_id": scenario.lineage_id, "version": scenario.version}


def build_simulation_report(simulation) -> dict:
    r = simulation.result
    return {**_header("simulation", simulation.scenario_type),
            "simulation_id": simulation.simulation_id, "scenario_id": simulation.scenario_id,
            "readiness_score": r.readiness_score, "readiness_status": r.readiness_status,
            "summary": r.summary, "outcomes": [o.to_dict() for o in r.outcomes],
            "version": simulation.version, "lineage_id": simulation.lineage_id}


def build_forecast_report(simulation) -> dict:
    r = simulation.result
    return {**_header("forecast", simulation.scenario_type),
            "simulation_id": simulation.simulation_id,
            "summary": forecast_summary(r.forecasts),
            "forecasts": [f.to_dict() for f in r.forecasts]}


def build_comparison_report(comparison) -> dict:
    return {**_header("comparison"),
            "comparison_id": comparison.comparison_id,
            "scenario_ids": list(comparison.scenario_ids),
            "recommended_scenario_id": comparison.recommended_scenario_id,
            "advantages": list(comparison.advantages), "risks": list(comparison.risks),
            "tradeoffs": list(comparison.tradeoffs),
            "governance_impact": comparison.governance_impact,
            "constraint_impact": comparison.constraint_impact,
            "explanation": comparison.explanation}


def build_risk_report(simulation) -> dict:
    r = simulation.result
    return {**_header("simulation_risk", simulation.scenario_type),
            "simulation_id": simulation.simulation_id, "summary": risk_summary(r.risks),
            "risks": [rk.to_dict() for rk in r.risks]}


def build_validation_report(scope: str, validation_report_dict: dict) -> dict:
    return {**_header("simulation_validation", scope), "validation": validation_report_dict}


def build_audit_report(audit_log: Any) -> dict:
    return {**_header("simulation_audit"), "verified": audit_log.verify(),
            "audit": audit_log.to_dict()}


def build_lineage_report(simulation, lineage_tracker: Any) -> dict:
    verified = lineage_tracker.verify_chain(simulation.lineage_id) if simulation.lineage_id \
        else False
    return {**_header("simulation_lineage", simulation.scenario_type),
            "simulation_id": simulation.simulation_id, "lineage_id": simulation.lineage_id,
            "lineage_verified": verified}
