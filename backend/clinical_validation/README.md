# `backend/clinical_validation` — Clinical Validation & Evidence Platform (DRP-6)

Closes the audit's **insufficient clinical validation evidence** blocker: turns the
production-candidate platform into an **evidence-supported** platform with benchmark,
performance, reliability, and calibration evidence + objective comparison + validation
readiness. The scope is *validation and evidence generation* and nothing else — no
model-architecture / training / serving / persistence / security / frontend / deployment
changes (all explicitly out of scope).

Decision record:
[`../../.gcc/decisions/ADR-0029`](../../.gcc/decisions/ADR-0029-drp6-clinical-validation.md).

## What it does

```
develop production models (reused DRP-2) -> benchmark (acc/prec/rec/F1/ROC-AUC/PR-AUC/
sensitivity/specificity + perf) -> calibrate (ECE/Brier + reliability curve) -> measure
reliability (repeatability/reproducibility/cross-run/cross-dataset/failure modes) ->
generate evidence -> compare models -> score readiness -> trace -> audit
```

`ClinicalValidationService.run_validation(feature_records)` runs the whole governed flow for
every production architecture and returns a `ValidationRunOutcome` (per-model
`ClinicalValidationRecord`s + an objective comparison).

## Reuse — no replacement systems

Models are developed/benchmarked/evaluated/compared via the reused DRP-2
`ProductionModelService`; the clinical layer reuses the DRP-2 deterministic metrics + the DRP-2
evaluation's confusion matrix (for sensitivity/specificity) and reliability bins (for the
calibration curve). It shares the single `ml.lineage` tracker + the shared `ImmutableAuditLog`.

## Determinism (NR-9/NR-10)

Deterministic clinical metrics enter every benchmark/evidence id + signature. Performance
measures (latency/memory/inference+training time) are reported but **never hashed** — the
performance record's id is content-addressed on the model only, and the evidence fingerprint is
over the deterministic artifact signatures. Given the same models, identical evidence reproduces.

## Reliability (DRP6-E)

Repeatability (re-development reproduces the benchmark signature), reproducibility (DRP-2
self-verified training), cross-run stability (DRP-2 perturbation set), cross-dataset stability
(accuracy delta across an alternate split), and failure modes (bad inputs handled gracefully).

## Traceability (DRP6-H)

`verify_chain` from a readiness node proves **Dataset → Model → Benchmark → Evaluation →
Evidence → Readiness Assessment** and reaches the patient.

## Readiness (DRP6-I)

Seven weighted dimensions — benchmark / reliability / calibration / evidence / registry / audit
/ lineage. A model's evidence can be `READY` only when all exist and validation passes.

## Boundary (NR-8)

Imports `ml` + sibling `backend` only; never imports `frontend`. Deterministic throughout:
identical models reproduce the same validation id + version + evidence.

## Run

```bash
python -m scripts.verify_drp6_clinical_validation     # the 15 final-validation criteria
python -m pytest tests/test_clinical_validation.py tests/test_clinical_validation_e2e.py
```

## Honest scope

This generates **real, structured, traceable** validation evidence and scores validation
readiness. The metrics reflect the platform's **untuned reference baselines on synthetic feature
data** (Gap G1) — they are *evidence about those baselines*, **not** a clinical-efficacy claim,
and **not** external clinical validation on real patient data or regulatory deployment
qualification (those require real labelled clinical cohorts + prospective + formal review, out
of scope for an in-repo platform).
