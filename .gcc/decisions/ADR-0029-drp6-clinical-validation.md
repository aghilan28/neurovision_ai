# ADR-0029 — DRP-6: Clinical Validation & Evidence Platform

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Deployment Remediation Program DRP-6 (post-audit remediation)
> **Builds on:** ADR-0001 … ADR-0028 (Productization P1–P10 + DRP-1 … DRP-5)
> **Resolves:** Audit blocker — *INSUFFICIENT CLINICAL VALIDATION EVIDENCE* (insufficient
> benchmark / external-validation / deployment-qualification evidence)
> **Enforces / honors:** AP-6/NR-9/NR-10 (determinism), AP-5/AP-8/NR-11 (traceability),
> AP-7/NR-8 (boundaries), NR-6 (reuse), AP-9/NR-5 (this record), NR-13 (scope), NR-2 (honesty)

## 1. Context

After DRP-1 … DRP-5, the Independent Production Reality Audit's remaining blocker was
**insufficient clinical validation evidence**. DRP-6 adds the governed clinical-validation &
evidence platform: benchmark, performance, reliability, and calibration evidence + objective
comparison + validation readiness. The scope is strictly validation and evidence generation:
no model-architecture / training / serving / persistence / security / frontend / deployment
changes (NR-13).

## 2. Decisions

### D1 — A new governed `backend/clinical_validation` subsystem
Adds benchmarks, evaluation, evidence, reliability, calibration, comparison, readiness,
registry, audit, lineage, reports, and schemas. It validates + generates evidence; it does not
retrain models or change business logic. As a `backend` package it obeys the import DAG
(imports `ml` + sibling `backend`, never `frontend`; enforced by `tests/test_boundaries.py`).

### D2 — Reuse the DRP-2 production-model program (no replacement systems)
Models are developed + benchmarked + evaluated + compared via the reused DRP-2
`ProductionModelService`. The clinical layer **reuses** the DRP-2 deterministic metrics and
adds **sensitivity + specificity** (from the DRP-2 evaluation's confusion matrix), a calibration
study (ECE/Brier + the binned reliability curve), a reliability study (repeatability /
reproducibility / cross-run / cross-dataset stability + failure modes), an objective comparison,
and aggregated evidence — over the DRP-1 datasets / DRP-3 serving outputs.

### D3 — Reuse the shared audit + lineage (no parallel systems)
Validation events are appended to the shared hash-chained `ImmutableAuditLog`; validation
lineage nodes are recorded in the single `ml.lineage` tracker. The chain
`Dataset -> Model -> Benchmark -> Evaluation -> Evidence -> Readiness Assessment`
`verify_chain`s to the patient.

### D4 — Deterministic verdicts; informational performance
Deterministic metrics (accuracy / precision / recall / F1 / ROC-AUC / PR-AUC / sensitivity /
specificity / ECE / Brier) enter every benchmark/evidence id + signature. Performance measures
(latency / memory / inference + training time) are reported but **never** enter a signature —
the performance record's id is content-addressed on the model only, and the evidence
fingerprint is over the deterministic artifact signatures — so verdicts reproduce bit-for-bit.

### D5 — Validation readiness with a hard gate
Seven weighted dimensions (benchmark / reliability / calibration / evidence / registry / audit /
lineage) → score + findings + NOT_READY / PARTIALLY_READY / READY. `READY` requires benchmarks +
reliability + calibration studies + evidence to exist, the registry + audit + lineage to exist,
validation to pass, and a readiness score to exist.

## 3. Consequences

- `python -m scripts.verify_drp6_clinical_validation` → **ALL 15 CRITERIA PASS** (stable across
  runs); every production model is benchmarked, evaluated, reliability- + calibration-measured,
  evidenced, compared, traced (Dataset → … → Readiness, reaching the patient), and scored
  **READY**.
- The new suite adds 15 tests; the full repository suite is **942 passed** (was 927). `ruff`
  clean on all new code; `tests/test_boundaries.py` green; prior verify scripts unaffected.
- No new runtime dependencies; the platform validates offline and deterministically.

## 4. Scope guard (explicitly NOT built — NR-13)

Model retraining, model-architecture changes, frontend changes, serving changes, persistence
changes, security changes, deployment changes, DRP-7+.

## 5. Honesty statement (NR-2)

DRP-6 generates **real, structured, traceable** validation evidence (benchmark / performance /
reliability / calibration / comparison) and scores validation readiness. The metrics reflect the
platform's **untuned reference baselines on synthetic feature data** (Gap G1 from the P10
certification) — they are *evidence about those baselines*, **not** a clinical-efficacy claim,
and do not constitute external clinical validation on real patient data or regulatory
deployment qualification. Those remain open conditions requiring real labelled clinical
cohorts, prospective evaluation, and formal clinical/regulatory review — out of scope for an
in-repo validation platform. This closes the *validation-evidence-generation* blocker: the
platform can now benchmark, measure reliability + calibration, generate evidence, trace it, and
score validation readiness reproducibly.
