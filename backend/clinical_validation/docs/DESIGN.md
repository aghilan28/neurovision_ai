# Clinical Validation & Evidence Platform — Design (DRP-6)

## Objective

Generate the clinical validation evidence the audit found missing: benchmark, performance,
reliability, and calibration evidence + objective comparison + validation readiness. Strictly
validation/evidence — no model / training / serving / persistence / security / frontend /
deployment changes.

## Package layout

```
backend/clinical_validation/
  version.py            component versions + DETERMINISTIC_EPOCH
  models/domain.py      closed vocabularies + 12 records (DRP6-B)
  identity/             mints validation_* ids; validates upstream model/dataset ids
  benchmarks/           build_benchmark (+ sensitivity/specificity) (DRP6-C)
  calibration/          build_calibration (ECE/Brier + reliability curve) (DRP6-D)
  reliability/          build_reliability (repeat/reproduce/cross-run/cross-dataset/fail) (DRP6-E)
  comparison/           build_comparison (DRP6-F)
  evidence/             build_evidence (DRP6-G)
  readiness/            ValidationReadinessEngine — 7 dimensions (DRP6-I)
  registry/             EvidenceRegistry (DRP6-G)
  audit/                make_validation_audit_log (shared ImmutableAuditLog) (DRP6-H)
  lineage/              validation lineage helpers (shared ml.lineage) (DRP6-H)
  validation/           content validators + integrity validator (ml.validation)
  reports/              ten deterministic report builders (DRP6-J)
  schemas/contracts.py  entity contracts (DRP6-K)
  service.py            ClinicalValidationService — the governed orchestration hub
```

## Reuse, not duplication

Models are developed/benchmarked/evaluated/compared via the reused DRP-2
`ProductionModelService`; the clinical layer reuses the DRP-2 deterministic metrics and the
DRP-2 evaluation's confusion matrix + reliability bins. It shares the single `ml.lineage`
tracker + the shared `ImmutableAuditLog`. The evidence registry stores only the new clinical
evidence artifacts.

## Determinism

Deterministic metrics (acc/prec/rec/F1/ROC-AUC/PR-AUC/sensitivity/specificity/ECE/Brier) enter
every benchmark/evidence id + signature. Performance measures (latency/memory/inference+training
time) are reported but never hashed: the performance record's id is content-addressed on the
model only, and the evidence fingerprint is over the deterministic artifact signatures. Given the
same models, identical evidence reproduces.

## Lineage chain (DRP6-H)

```
benchmark node parents the production-model node
evaluation node parents the benchmark node
evidence node parents the evaluation node
readiness node parents the evidence node
```

`verify_chain(readiness)` proves Dataset → Model → Benchmark → Evaluation → Evidence → Readiness
and reaches the patient.

## Readiness criteria

`READY` ⇔ benchmark + reliability + calibration studies + evidence exist ∧ registry + audit +
lineage exist ∧ validation passes ∧ a readiness score exists. Otherwise `PARTIALLY_READY` or
`NOT_READY`.

## Honest scope

The metrics reflect untuned reference baselines on synthetic feature data (Gap G1) — they are
evidence about those baselines, not a clinical-efficacy claim, and not external clinical
validation on real patient data. Out of scope: model retraining, architecture/serving/
persistence/security/deployment changes, DRP-7+.
