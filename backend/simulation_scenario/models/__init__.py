"""Simulation/scenario domain entities (V4-P9)."""

from __future__ import annotations

from .domain import (
    ScenarioType, SCENARIO_TYPES, SimDimension, SIM_DIMENSIONS, ForecastType, FORECAST_TYPES,
    SimRiskDimension, SIM_RISK_DIMENSIONS, OutcomeStatus,
    ScenarioContext, ScenarioRecord, SimulationOutcome, ForecastRecord, SimulationRiskRecord,
    SimulationResult, SimulationRecord, ComparisonRecord, SimulationVersion,
    SimulationAuditRecord, SimulationLineageRecord, SimulationRegistryRecord,
)
from .context import (
    SimulationView, build_context, observations_from_context,
)

__all__ = [
    "ScenarioType", "SCENARIO_TYPES", "SimDimension", "SIM_DIMENSIONS", "ForecastType",
    "FORECAST_TYPES", "SimRiskDimension", "SIM_RISK_DIMENSIONS", "OutcomeStatus",
    "ScenarioContext", "ScenarioRecord", "SimulationOutcome", "ForecastRecord",
    "SimulationRiskRecord", "SimulationResult", "SimulationRecord", "ComparisonRecord",
    "SimulationVersion", "SimulationAuditRecord", "SimulationLineageRecord",
    "SimulationRegistryRecord", "SimulationView", "build_context", "observations_from_context",
]
