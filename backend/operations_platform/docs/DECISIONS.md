# Operational Readiness & Deployment Qualification — Decisions (Track 4)

Canonical record: [`ADR-0033`](../../../.gcc/decisions/ADR-0033-track4-operational-qualification.md).

- **New observe-only subsystem.** `operations_platform` qualifies the Track-3 product
  **read-only** — it constructs nothing in the product and re-runs no business logic; it
  inspects already-produced state. Distinct from the top-level P8 `operations/` ops layer.
- **Health / monitoring / diagnostics / qualification / readiness** over the real product:
  HEALTHY/DEGRADED/UNHEALTHY, deterministic volume counts, closed root-cause classification,
  target-availability qualification, and a `READY_FOR_DEPLOYMENT` verdict.
- **Shared lineage + audit, no parallel systems.** Uses the product's `ml.lineage` tracker so
  the operational chain attaches to the product workflow (Dataset → Model → Prediction →
  Workflow → Health Event → Qualification Event); events on the shared `ImmutableAuditLog`.
- **Determinism.** Content-addressed ids over observed deterministic state; wall-clock measures
  informational and excluded from signatures + the deterministic reports.
- **Scope (NR-13).** No retraining / dataset / Track-1/2/3 / prediction-logic / security /
  deployment-infrastructure changes; no new AI / architecture.
- **Honesty (NR-2).** `READY_FOR_DEPLOYMENT` certifies the in-repo product is operationally
  qualified (observable / diagnosable / qualified / traceable), not that a production cluster
  is provisioned (TLS/autoscaling/secrets/orchestration remain out of scope).
