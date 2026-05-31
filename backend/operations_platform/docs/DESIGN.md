# Operational Readiness & Deployment Qualification — Design (Track 4)

## Objective

Turn the usable product (Track 3) into a **deployable product**: qualify operations — health,
monitoring, diagnostics, deployment qualification, and deployment readiness — over the real
application platform, proving the system is objectively `READY_FOR_DEPLOYMENT`.

## Module map

| Module | Phase | Responsibility |
|---|---|---|
| `version.py` | — | version coordinates + `DETERMINISTIC_EPOCH` |
| `models/domain.py` | T4-A/B | closed vocabularies + records (health/metrics/diagnostic/qualification/readiness/registry/audit) |
| `identity/` | — | content-addressed `{kind}+{hash16}` ids over observed state |
| `health/` | T4-B | `HealthEngine` — 7 components → HEALTHY/DEGRADED/UNHEALTHY + overall |
| `monitoring/` | T4-C | `MonitoringEngine` — deterministic volume/failure counts + informational measures |
| `diagnostics/` | T4-D | `DiagnosticEngine` — workflow/prediction/upload/API/failure + root-cause classification |
| `qualification/` | T4-E | `QualificationEngine` — dataset/model/API/workflow/report/persistence/security availability |
| `readiness/` | T4-F | `DeploymentReadinessEngine` — NOT_READY / PARTIALLY_READY / READY_FOR_DEPLOYMENT |
| `registry/` | T4-G | `OperationsRegistry` — no orphan records |
| `audit/` | T4-G | the shared `ImmutableAuditLog` (no parallel system) |
| `lineage/` | T4-G | shared `ml.lineage`; Dataset → Model → Prediction → Workflow → Health → Qualification |
| `reports/` | T4-H | 8 deterministic reports |
| `schemas/` | — | a documented contract per entity |
| `service.py` | — | `OperationsPlatformService(product)` — `qualify()` / `reports()` |

## Qualification flow

`OperationsPlatformService(product).qualify()`:
1. **T4-B** health-check the real product → mint a health-event lineage node parenting the
   product's completed-workflow node(s);
2. **T4-C** monitoring snapshot (deterministic counts + informational measures);
3. **T4-D** diagnostics (root-cause classification);
4. **T4-E** deployment qualification (target availability) → qualification-event node parents
   the health-event node;
5. **T4-F** deployment readiness → readiness node parents the qualification-event node;
6. register every entity (no orphans), append audit events, verify the lineage chain.

## Reuse (no parallel systems, observe-only)

The subject is the real Track-3 `ApplicationPlatformService`; Track 4 reads its
`.lineage` / `.registry` / `.audit` / `._model_info` / `._analyses` and its completed
`AnalysisOutcome`s. It shares the product's lineage tracker (so the operational chain attaches
to the product workflow) and uses the shared `ImmutableAuditLog`. It re-runs no business logic.

## Determinism

Ids/fingerprints are content-addressed over the observed deterministic state. Wall-clock
latency / processing-time / resource measures are informational and excluded from every
signature and from the deterministic reports (the monitoring report lists the names of the
informational measures tracked, not their volatile values), so a given observed product
reproduces the same health/qualification/readiness ids + byte-identical reports.

## Test strategy

* **Network-free** tests build a real Track-3 product (model from committed real EDF fixtures,
  a real EEG analysed through the real FastAPI workflow), then qualify it — covering health,
  monitoring, diagnostics, qualification, readiness, audit, lineage, registry, reports,
  determinism, and the missing-model / missing-dataset / API-failure / corrupted-state
  conditions.
* A **real-corpus** test qualifies a product built from the locally-acquired PhysioNet
  recordings when available.
