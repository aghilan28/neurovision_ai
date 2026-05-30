# V4-P7 — Governance Intelligence Layer

## Objective

Make governance a first-class **intelligence** system: observable, analyzable,
auditable, and explainable. This phase creates *intelligence about governance*; it
does **not** create new governance rules, modify governance, or bypass policy and
approval workflows.

## Domain model

| Entity | Role |
|--------|------|
| `GovernanceIntelligenceIdentity` | content-addressed id (`govintel+{hash16}`) |
| `GovernanceIntelligenceRecord` | aggregate snapshot (approvals + violations + escalations + risks + metrics + health) |
| `ApprovalRecord` | per-entity approval intelligence (logical latency, decision, authority) |
| `ViolationRecord` | a detected violation (type + severity + impact) |
| `EscalationRecord` | escalation intelligence (outcome, logical delay, risk, effectiveness) |
| `GovernanceRiskRecord` | explainable risk score for one (dimension, entity) |
| `GovernanceMetric` | a single deterministic analytics metric |
| `GovernanceVersion` | content-addressed, chained version |
| `GovernanceAuditRecord` | immutable audit event (shared `ImmutableAuditLog`) |
| `GovernanceLineageRecord` | lineage projection |
| `GovernanceRegistryRecord` | registry entry |

## Observation source view

`GovernanceObservationView.from_sources(goals=…, policies=…, constraints=…, plans=…,
tasks=…, agents=…, executions=…)` normalizes every governed entity into a uniform,
read-only `GovernedObservation` (approval/authorization state, governance history,
escalation flag, policy references, lifecycle state, lineage node). The engines
reason over these observations identically.

## Intelligence engines

- **Approvals** — goal/plan/task/agent approvals + execution authorizations →
  per-entity `ApprovalRecord` + aggregate metrics (latency, backlog, failures,
  throughput, health).
- **Violations** — detect lifecycle / approval / authorization / governance / policy /
  constraint violations, with severity and impact. A clean platform yields **zero**.
- **Escalations** — escalation requests, outcomes, logical delays, risks,
  effectiveness.
- **Risk** — explainable [0,1] scores across approval / execution / policy /
  constraint / assignment / governance dimensions, each with factors + explanation.
- **Analytics** — governance metrics, trends, a composite health score, bottlenecks.
- **Monitoring** — which executions require intervention; what state requires human
  review.

## Governed admission path

`build()` derives the record, then admits it through one governed path:
governance-intelligence gate → shared-lineage node (parented by the observed
artifacts' lineage nodes) → immutable audit event → content-addressed version →
registry sync + index.

## Determinism & traceability

No wall-clock anywhere; latencies/delays are logical governance-event counts. Because
the record's lineage parents are the observed artifacts' nodes, `verify_chain` from a
governance-intelligence record spans **Patient → … → Goal → Policy → Plan → Task →
Agent → Execution → Governance Intelligence**.

## Out of scope (NR-13)

No governance-rule creation, no autonomous policy updates, no simulation / scenario /
forecasting engines, no Version 5 features. Governance intelligence observes; it
never modifies governance.
