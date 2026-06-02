"""``backend/simulation_scenario`` — Simulation & Scenario Layer (V4-P9).

A **governed simulation environment** for the platform. It exists to *evaluate*
possible futures — not to execute, authorize, or modify production state. Simulation
is observational intelligence: deterministic (no randomness), explainable, traceable,
governed, auditable, and recoverable, derived from the already-governed Version 4
artifacts (goals, policies, constraints, plans, tasks, agents, executions) and the
V4-P7 governance intelligence.

It answers the questions the platform could not safely answer before: *what should
happen before execution? what risks exist across possible futures? how should
competing execution paths be evaluated?* — through a scenario engine, a simulation
engine, a forecast layer, a comparison engine, and a simulation risk engine.

Every artifact is versioned, traceable, auditable, lineage-tracked, governed,
deterministic, explainable, and recoverable. Lineage parents are the evaluated
artifacts' nodes, so ``verify_chain`` reaches the patient. Shares the platform's
single ``ml.lineage.LineageTracker`` and the shared ``ImmutableAuditLog`` — no
parallel lineage/audit/governance.

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` and sibling
``backend`` subsystems; never imports ``frontend``. Strictly V4-P9 — simulation +
scenario evaluation + outcome forecast structures only. **Simulation may observe.
Simulation may evaluate. Simulation may never execute.** No autonomous goal/policy
creation, no autonomous governance modification, no Version 5 features.
"""

from __future__ import annotations

from .version import (
    SIMULATION_SCENARIO_VERSION, SIMULATION_DOMAIN_VERSION, SIMULATION_IDENTITY_VERSION,
    SIMULATION_CONTEXT_VERSION, SIMULATION_ENGINE_VERSION, SIMULATION_FORECAST_VERSION,
    SIMULATION_COMPARISON_VERSION, SIMULATION_RISK_VERSION, SIMULATION_REGISTRY_VERSION,
    SIMULATION_AUDIT_VERSION, SIMULATION_LINEAGE_VERSION, SIMULATION_VALIDATION_VERSION,
    SIMULATION_REPORT_VERSION,
)
from .identity import (
    ScenarioIdentity, SimulationIdentityError, mint_scenario, mint_simulation, mint_forecast,
    mint_comparison, mint_risk, validate_scenario_identity, validate_simulation_identity,
)
from .models import (
    ScenarioType, SCENARIO_TYPES, SimDimension, SIM_DIMENSIONS, ForecastType, FORECAST_TYPES,
    SimRiskDimension, SIM_RISK_DIMENSIONS, OutcomeStatus, ScenarioContext, ScenarioRecord,
    SimulationOutcome, ForecastRecord, SimulationRiskRecord, SimulationResult, SimulationRecord,
    ComparisonRecord, SimulationVersion, SimulationAuditRecord, SimulationLineageRecord,
    SimulationRegistryRecord, SimulationView, build_context, observations_from_context,
)
from .scenarios import (
    build_scenario, goal_scenario, plan_scenario, task_scenario, agent_scenario,
    execution_scenario, governance_scenario, risk_scenario,
)
from .simulation import run_simulation
from .evaluation import evaluate
from .forecast import build_forecasts, forecast_summary
from .comparison import build_comparison
from .risk import build_risks, risk_summary
from .governance import SimulationGate, SimulationGovernanceError
from .registry import SimulationRegistry
from .validation import SimulationValidator
from .audit import make_simulation_audit_log
from .service import SimulationScenarioService

__all__ = [
    "SIMULATION_SCENARIO_VERSION", "SIMULATION_DOMAIN_VERSION", "SIMULATION_IDENTITY_VERSION",
    "SIMULATION_CONTEXT_VERSION", "SIMULATION_ENGINE_VERSION", "SIMULATION_FORECAST_VERSION",
    "SIMULATION_COMPARISON_VERSION", "SIMULATION_RISK_VERSION", "SIMULATION_REGISTRY_VERSION",
    "SIMULATION_AUDIT_VERSION", "SIMULATION_LINEAGE_VERSION", "SIMULATION_VALIDATION_VERSION",
    "SIMULATION_REPORT_VERSION",
    "ScenarioIdentity", "SimulationIdentityError", "mint_scenario", "mint_simulation",
    "mint_forecast", "mint_comparison", "mint_risk", "validate_scenario_identity",
    "validate_simulation_identity",
    "ScenarioType", "SCENARIO_TYPES", "SimDimension", "SIM_DIMENSIONS", "ForecastType",
    "FORECAST_TYPES", "SimRiskDimension", "SIM_RISK_DIMENSIONS", "OutcomeStatus",
    "ScenarioContext", "ScenarioRecord", "SimulationOutcome", "ForecastRecord",
    "SimulationRiskRecord", "SimulationResult", "SimulationRecord", "ComparisonRecord",
    "SimulationVersion", "SimulationAuditRecord", "SimulationLineageRecord",
    "SimulationRegistryRecord", "SimulationView", "build_context", "observations_from_context",
    "build_scenario", "goal_scenario", "plan_scenario", "task_scenario", "agent_scenario",
    "execution_scenario", "governance_scenario", "risk_scenario", "run_simulation", "evaluate",
    "build_forecasts", "forecast_summary", "build_comparison", "build_risks", "risk_summary",
    "SimulationGate", "SimulationGovernanceError", "SimulationRegistry", "SimulationValidator",
    "make_simulation_audit_log", "SimulationScenarioService",
]
