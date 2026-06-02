# V4-P9 — Simulation & Scenario Layer

## Objective

Create a **governed simulation environment** that evaluates possible futures. It
exists to evaluate — **not** to execute, authorize, or modify production state.
Simulation is observational intelligence: deterministic, explainable, traceable,
governed, auditable, recoverable.

## Domain model

| Entity | Role |
|--------|------|
| `ScenarioIdentity` | content-addressed id (`scenario+{hash16}`) |
| `ScenarioContext` | frozen, content-addressed snapshot of observed artifacts + what-if assumptions |
| `ScenarioRecord` | a reproducible hypothesis of a given type |
| `SimulationRecord` | a deterministic evaluation run of a scenario |
| `SimulationResult` | aggregate: outcomes + forecasts + risks + readiness |
| `SimulationOutcome` | per-dimension deterministic outcome |
| `ForecastRecord` | explainable projected outcome |
| `ComparisonRecord` | comparison across scenarios + recommendation |
| `SimulationRiskRecord` | explainable simulation-risk score |
| `SimulationVersion` / `SimulationAuditRecord` / `SimulationLineageRecord` / `SimulationRegistryRecord` | version / audit / lineage / registry |

## Engines

- **Scenario engine** — reproducible goal / plan / task / agent / execution / governance /
  risk scenarios over a `SimulationView` (reuses the V4-P7 `GovernanceObservationView`).
- **Simulation engine** — deterministically evaluates a scenario: policy effects,
  constraint effects, task dependencies, agent availability, execution structures,
  governance controls → outcomes (no randomness).
- **Forecast layer** — execution / risk / governance / approval / constraint forecasts,
  each with a derived (never random) confidence and an explanation.
- **Comparison engine** — compares ≥2 simulated scenarios → advantages, risks,
  tradeoffs, governance impact, constraint impact, and a recommended scenario.
- **Simulation risk engine** — explainable risk scores across execution / governance /
  policy / agent / dependency / scenario dimensions.

## What-if assumptions (evaluation-only)

`exclude_agents`, `blocked_executions`, `strict_policies` adjust the evaluation
**only inside the simulation** — production state is never touched. Different
assumptions yield different readiness/risk, which the comparison engine ranks.

## Governed admission path

`create_scenario` / `simulate` / `compare` each admit through one governed path:
simulation gate → shared-lineage node (parented by the evaluated artifacts' nodes) →
immutable audit event → content-addressed version → registry sync + index.

## Determinism & traceability

No wall-clock, no randomness. Because a simulation's lineage parents are its scenario
node + the evaluated artifacts' nodes, `verify_chain` spans **Patient → … → Execution
→ Governance Intelligence → Scenario → Simulation**.

## Out of scope (NR-13 / forbidden work)

No Version 5 features, no distributed intelligence, no multi-site federation, no
self-modifying systems, no autonomous goal/policy creation, no autonomous governance
modification, no realtime EEG or hospital-deployment systems. Simulation evaluates; it
never executes.
