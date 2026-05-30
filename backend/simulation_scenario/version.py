"""Version identities for the Simulation & Scenario Layer (V4-P9).

Every simulation artifact records the versions that produced it, so it is reproducible
and auditable for its whole lifetime (AP-5/AP-6/AP-9, NR-10/NR-11).

The simulation layer is a **governed evaluation environment**. It exists to *evaluate*
possible futures — never to execute, authorize, or modify production state. It is
observational intelligence: deterministic (no randomness), explainable, traceable, and
derived from the already-governed Version 4 artifacts (goals, policies, constraints,
plans, tasks, agents, executions, governance intelligence). Every scenario/simulation/
forecast/comparison/risk it produces traces, through lineage, back to those artifacts
and onward to the patient.
"""

from __future__ import annotations

SIMULATION_SCENARIO_VERSION: str = "simulation-scenario@1.0.0"

SIMULATION_DOMAIN_VERSION: str = "simulation-domain@1.0.0"
SIMULATION_IDENTITY_VERSION: str = "simulation-identity@1.0.0"
SIMULATION_CONTEXT_VERSION: str = "simulation-context@1.0.0"
SIMULATION_SCENARIO_ENGINE_VERSION: str = "simulation-scenario-engine@1.0.0"
SIMULATION_ENGINE_VERSION: str = "simulation-engine@1.0.0"
SIMULATION_EVALUATION_VERSION: str = "simulation-evaluation@1.0.0"
SIMULATION_FORECAST_VERSION: str = "simulation-forecast@1.0.0"
SIMULATION_COMPARISON_VERSION: str = "simulation-comparison@1.0.0"
SIMULATION_RISK_VERSION: str = "simulation-risk@1.0.0"
SIMULATION_GOVERNANCE_VERSION: str = "simulation-governance@1.0.0"
SIMULATION_REGISTRY_VERSION: str = "simulation-registry@1.0.0"
SIMULATION_AUDIT_VERSION: str = "simulation-audit@1.0.0"
SIMULATION_LINEAGE_VERSION: str = "simulation-lineage@1.0.0"
SIMULATION_VALIDATION_VERSION: str = "simulation-validation@1.0.0"
SIMULATION_REPORT_VERSION: str = "simulation-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
