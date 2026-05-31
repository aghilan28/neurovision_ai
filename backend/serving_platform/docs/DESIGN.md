# Production Serving Platform — Design (DRP-3)

## Objective

Provide the serving boundary the audit found missing: receive prediction requests, select
models, execute inference, generate + deliver responses, track the lifecycle, score
readiness, trace lineage, and audit execution. Strictly serving infrastructure — no
model/training/frontend/deployment/operations/security/persistence/inference-architecture
changes.

## Package layout

```
backend/serving_platform/
  version.py            component versions + DETERMINISTIC_EPOCH
  models/domain.py      closed vocabularies + 11 records (DRP3-B)
  identity/             mints serving_request/serving_execution/serving_response/
                        serving_readiness; validates upstream ids
  contracts/            versioned service contracts (DRP3-E)
  routing/              ModelRouter — resolution / selection / version selection (DRP3-C)
  execution/            ModelServingEngine — catalog + reused inference execution (DRP3-C)
  services/             PredictionService — response delivery (DRP3-D)
  lifecycle/            LifecycleTracker — 7-state lifecycle (DRP3-F)
  validation/           content validators + integrity validator (DRP3-G; ml.validation)
  registry/             ServingRegistry (DRP3-H)
  readiness/            ServingReadinessEngine — 6 dimensions (DRP3-I)
  lineage/              serving lineage helpers (shared ml.lineage) (DRP3-J)
  audit/                make_serving_audit_log (shared ImmutableAuditLog) (DRP3-J)
  reports/              nine deterministic report builders (DRP3-K)
  schemas/contracts.py  entity contracts (DRP3-L)
  service.py            ServingPlatformService — the governed orchestration hub
```

## Domain records (DRP3-B)

`ServingIdentity`, `ServingRequestRecord`, `ServingResponseRecord`, `ServingExecutionRecord`,
`ServingLifecycleRecord`, `ServingValidationRecord`, `ServingRegistryRecord`,
`ServingReadinessRecord`, `ServingAuditRecord`, `ServingLineageRecord`, `ServingVersion`.
Closed vocabularies only.

## Reuse, not duplication

- `InferenceFoundationService.predict` for execution (DRP3-D — no duplicated prediction
  logic); the serving engine holds the servable model record + the train feature assets the
  inference foundation needs to reconstruct + verify the model.
- shared `ml.lineage.LineageTracker` + shared `ImmutableAuditLog` + `ml.validation`.
- the underlying model lives in the shared `ModelRegistry`; the serving registry stores only
  the new serving artifacts (no parallel registry).

## Lineage chain

```
request node parents [model node, feature node]
prediction node (from inference foundation) parents [model node, feature node]
execution node parents [request node, prediction node]
response node parents [execution node]
```

`verify_chain(response.lineage_id)` reaches the patient, covering Dataset → Feature → Model
→ Inference → Serving Request → Serving Execution → Serving Response.

## Determinism

No wall-clock, no randomness anywhere in the serving path. Ids/versions are content-addressed
(`serving_request`/`serving_execution`/`serving_response`), so serving the same request twice
is idempotent and reproduces the same execution id + version. The version's state signature
excludes `version_integrity` (a post-build integrity check) to avoid self-reference.

## Readiness criteria

`READY` ⇔ requests + responses + the lifecycle work ∧ validation passes ∧ registry + audit +
lineage exist ∧ a readiness score exists. Otherwise `PARTIALLY_READY` (score ≥ 0.5, validation
ok) or `NOT_READY`.

## Out of scope (forbidden in DRP-3)

Frontend changes, model retraining, deployment changes, operations changes, security changes,
persistence changes, clinical validation, inference-architecture changes, DRP-4+.
