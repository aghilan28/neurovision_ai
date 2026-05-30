# `backend/governance_intelligence` — Governance Intelligence Layer (V4-P7)

Makes **governance a first-class intelligence system**. Governance becomes
**observable, analyzable, auditable, and explainable** — without creating any new
governance rule, modifying governance state, or bypassing policy/approval workflows.
This layer produces *intelligence about governance*, derived deterministically from
the already-governed Version 4 artifacts.

## What it answers

- **What governance risks exist?** → the governance risk engine (`risk/`).
- **What governance violations exist?** → violation intelligence (`violations/`).
- **Which executions require intervention?** → monitoring (`monitoring/`).
- **Which approvals are bottlenecks?** → approval intelligence (`approvals/`).
- **What operational state requires human review?** → monitoring (`monitoring/`).

## Principle: observe, never modify

Governance intelligence **may observe governance** (goals, policies, constraints,
plans, tasks, agents, executions). It **may not modify governance** — it creates no
rules, makes no approval decisions, and bypasses no workflow. The
`GovernanceIntelligenceGate` encodes this invariant (risk + governance dimensions).

## Structure

| Path | Responsibility |
|------|----------------|
| `models/` | domain entities + the read-only `GovernanceObservationView` source view |
| `identity/` | content-addressed identities (`govintel+…`, `govapproval+…`, …) |
| `approvals/` | approval intelligence: latency, backlog, failures, throughput, health |
| `violations/` | violation detection: policy/constraint/governance/approval/authorization/lifecycle + severity + impact |
| `escalations/` | escalation intelligence: requests, outcomes, delays, risks, effectiveness |
| `risk/` | governance risk engine: explainable scores across six dimensions |
| `analytics/` | governance metrics, trends, health score, bottlenecks |
| `monitoring/` | which executions require intervention; what state requires human review |
| `registry/` | versioned, traceable registry of intelligence records + sub-indexes |
| `governance/` | the five-dimension admission gate (observe-only invariant) |
| `validation/` | the nine mandated integrity checks |
| `audit/` | the shared `ImmutableAuditLog` bound to `GovernanceAuditRecord` |
| `lineage/` | lineage nodes parented by the observed artifacts' nodes |
| `reports/` | approval / violation / escalation / risk / analytics / validation / audit / lineage reports |
| `schemas/` | per-entity contracts |
| `service.py` | `GovernanceIntelligenceService` — the governed orchestration hub |

## Determinism, lineage, audit

Everything is deterministic (no wall-clock; latencies/delays are **logical**
governance-event counts). Each record's lineage parents are the observed artifacts'
lineage nodes, so `verify_chain` from a governance-intelligence record reaches the
**patient**. The subsystem shares the single platform `ml.lineage.LineageTracker`
and the shared `ImmutableAuditLog` — no parallel lineage/audit/governance.

## Boundary (NR-8)

Part of the `backend` Application layer. Imports `ml` and sibling `backend`
subsystems; never imports `frontend`. Strictly V4-P7: no governance-rule creation,
no autonomous policy updates, no simulation/scenario/forecasting engines, no
Version 5 features.
