# `backend/serving_platform` — Production Serving Platform (DRP-3)

Closes the audit's **no serving layer** blocker: turns the model platform into a **serving
platform** with an inference service boundary, a model serving lifecycle, and an in-process
public execution interface. The scope is *serving infrastructure* and nothing else — no
model-architecture / training / frontend / deployment / operations / security / persistence
changes, and no inference-architecture changes (all explicitly out of scope).

Decision record:
[`../../.gcc/decisions/ADR-0026`](../../.gcc/decisions/ADR-0026-drp3-serving-platform.md).

## What it does

```
receive request -> validate -> select model (resolve / version) -> execute inference
(reused) -> generate response (prediction + confidence + calibration + explanation) ->
deliver -> complete -> validate -> score readiness -> version -> register ->
record lineage -> audit
```

`ServingPlatformService.load_model(model_record, train_feature_records, ...)` makes an
already-trained model servable (this layer never trains). `serve(request, input)` runs the
whole governed flow and returns a `ServingOutcome`.

## Reuse — no parallel systems (DRP3-D / DRP3-J)

- **Inference execution:** delegates to the reused `InferenceFoundationService` — it
  **duplicates no prediction logic**. The response carries the inference asset's prediction,
  confidence, calibration, and explanation (faithful uncertainty, NR-4).
- **Models:** serves `model_foundation` model records (the inference-foundation-servable
  artifact); coexists with the DRP-2 production-model program on the shared lineage tracker.
- **Lineage + audit:** the single shared `ml.lineage.LineageTracker` and the shared
  `ImmutableAuditLog`. The serving registry stores only the new serving artifacts (requests,
  executions, responses, readiness) — no parallel model / prediction registry.

## Model serving engine (DRP3-C) + routing

A catalog of servable models (record + the feature assets the inference foundation needs to
reconstruct + verify them). The `ModelRouter` resolves a `model_ref` by `model_id`, by
`architecture` + explicit `version`, or by `architecture` (latest loaded) — deterministically.

## Execution lifecycle (DRP3-F)

`request_created → request_validated → model_selected → inference_executed →
response_generated → response_delivered → execution_completed`, tracked and order-validated.

## Readiness (DRP3-I)

Six weighted dimensions — execution / contract / validation / registry / audit / lineage. A
serving execution can be `READY` only when requests + responses + the lifecycle work,
validation passes, the registry + audit + lineage exist, and a readiness score exists;
otherwise `PARTIALLY_READY` or `NOT_READY`.

## Traceability (DRP3-J)

A single `verify_chain` from a served response reaches the patient:

```
Dataset -> Feature Asset -> Model -> Inference -> Serving Request ->
Serving Execution -> Serving Response
```

## Graceful failure

Invalid requests, feature mismatches, and missing/unloaded models are rejected with a
structured `Error` contract (`REQUEST_INVALID` / `FEATURE_MISMATCH` / `FEATURE_UNAVAILABLE`
/ `MODEL_NOT_FOUND`) and audited — never a crash, and nothing is half-registered.

## Boundary (NR-8)

Imports `ml` + sibling `backend` only; never imports `frontend`. No HTTP / networking /
serving infrastructure beyond the in-process service contracts. Deterministic throughout
(no wall-clock, no randomness): identical requests reproduce the same execution id + version.

## Run

```bash
python -m scripts.verify_drp3_serving_platform     # the 15 final-validation criteria
python -m pytest tests/test_serving_platform.py tests/test_serving_platform_e2e.py
```

## Honest scope

This adds the serving **boundary, lifecycle, and execution interface** in-process. It does
**not** add an HTTP/network transport, deployment, or persistence (those are out of scope /
later phases). Predictions reflect the underlying untuned reference models on synthetic data
(Gap G1) — the serving layer faithfully delivers their uncertainty, never a clinical claim.
