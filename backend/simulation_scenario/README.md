# `backend/simulation_scenario` — Simulation & Scenario Layer (V4-P9)

A **governed simulation environment**. It exists to **evaluate** possible futures —
**never to execute, authorize, or modify production state**. Simulation is
observational intelligence: deterministic (no randomness), explainable, traceable,
governed, auditable, and recoverable, derived from the already-governed Version 4
artifacts (goals, policies, constraints, plans, tasks, agents, executions) and the
V4-P7 governance intelligence.

## What it answers

- **What should happen before execution?** → scenarios + the simulation engine.
- **What risks exist across possible futures?** → the simulation risk engine + forecasts.
- **How should competing execution paths be evaluated?** → the comparison engine.

## Principle: evaluate, never execute

Simulation **may observe** and **may evaluate**. It **may never execute**, authorize,
commit, or deploy. The `SimulationGate` rejects any artifact whose statuses claim a
real action occurred.

## Structure

| Path | Responsibility |
|------|----------------|
| `models/` | domain entities + `ScenarioContext` + the read-only `SimulationView` source view |
| `identity/` | content-addressed identities (`scenario+…`, `sim+…`, `simfc+…`, `simcmp+…`, `simrisk+…`) |
| `scenarios/` | scenario engine — reproducible goal/plan/task/agent/execution/governance/risk scenarios |
| `simulation/` | simulation engine — deterministic scenario evaluation into a result |
| `evaluation/` | deterministic effect evaluators (policy/constraint/dependency/agent/execution/governance) |
| `forecast/` | forecast layer — execution/risk/governance/approval/constraint forecasts |
| `comparison/` | comparison engine — advantages/risks/tradeoffs/impact + a recommendation |
| `risk/` | simulation risk engine — explainable scores across six dimensions |
| `registry/` | versioned registry of scenarios/simulations/comparisons + sub-indexes |
| `governance/` | the five-dimension admission gate (evaluate-only invariant) |
| `validation/` | the eight mandated integrity checks |
| `audit/` | the shared `ImmutableAuditLog` bound to `SimulationAuditRecord` |
| `lineage/` | lineage nodes parented by the evaluated artifacts' nodes |
| `reports/` | scenario / simulation / forecast / comparison / risk / validation / audit / lineage reports |
| `schemas/` | per-entity contracts |
| `service.py` | `SimulationScenarioService` — the governed orchestration hub |

## Determinism, lineage, audit

Everything is deterministic — no wall-clock, **no randomness**; the same scenario
always yields the same simulation. Each artifact's lineage parents are the evaluated
artifacts' nodes (a simulation also parents its scenario; a comparison parents its
simulations), so `verify_chain` from a simulation reaches the **patient**. Shares the
single platform `ml.lineage.LineageTracker` and the shared `ImmutableAuditLog`.

## Boundary (NR-8)

Part of the `backend` Application layer. Imports `ml` and sibling `backend`
subsystems (reuses the V4-P7 `GovernanceObservationView`); never imports `frontend`.
Strictly V4-P9: no autonomous goal/policy creation, no autonomous governance
modification, no Version 5 features.
