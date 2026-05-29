# `backend/offline_inference/` — Offline Inference Platform (V1-P7)

> **Layer:** Application (`backend/`) · **Status:** Implemented (offline, V1-P7).
> **Decision record:** [`../../.gcc/decisions/ADR-0002`](../../.gcc/decisions/ADR-0002-v1-p7-p8-offline-inference-and-research-app.md)
> **Governing docs:** AP-4/NR-4 (uncertainty), AP-5/AP-8/NR-11 (traceability/audit),
> AP-6/NR-9/NR-10 (determinism), AP-7/NR-8 (boundaries)

The orchestration layer that connects **every Version 1 subsystem** into one
deterministic, offline workflow: **raw EEG → intelligence output**, fully
versioned, traceable, and auditable. Offline only — no APIs, networking, real-time,
multi-user, or clinical deployment (those are V2+).

---

## The 15-stage pipeline

```
Dataset Ingestion → Validation → Preprocessing → Dataset Intelligence →
Evaluation Preparation → Model Selection → Inference → Calibration →
Conformal Prediction → Coverage Validation → Risk Assessment →
Output Generation → Artifact Registration → Lineage Registration → Audit Generation
```

Each stage is versioned, returns a content signature, and is independently
auditable. The `ExecutionEngine` records per-stage status + timing (timing is
non-hashed) and supports failure capture + recovery (resume).

## Subsystems

| Subsystem | Role |
|-----------|------|
| `orchestrator/` | `InferenceOrchestrator` — the 15-stage master workflow. |
| `pipelines/` | `PipelineConfig` — pinned, content-addressed run configuration. |
| `execution/` | deterministic `ExecutionEngine` (status/timing/failure/recovery). |
| `jobs/` | `JobRunner` + Inference/Batch/Validation/Audit/Artifact/Report jobs (recoverable, auditable). |
| `registry/` | `InferenceRegistry` — no inference exists outside it. |
| `artifacts/` | checksummed artifact store (+ `verify_directory` tamper detection). |
| `lineage/` | content-addressed inference lineage (parents: training→evaluation→uncertainty). |
| `validation/` | `InferenceValidator` — 7 integrity checks. |
| `reports/` | inference/calibration/coverage/risk/summary/audit reports. |
| `schemas/` | 10 typed output contracts. |

## Boundary (NR-8)

`backend` imports `ml`, `evaluation`, `datasets`, `preprocessing` and **composes**
them (it re-implements nothing). It **never** imports `frontend`. The
`ml ↛ evaluation` rule still holds: the orchestrator (above both) wires model
outputs through the evaluation framework via the `EvaluationPort`.

## Run it

```bash
python -m scripts.run_offline_inference --model tcn --render-app
python -m scripts.verify_v1          # 15 final-validation criteria
```

Outputs are written to a run directory (registered, checksummed):
`inference_index.json`, `outputs/*_output.json`, `reports/*.json`,
`registries/*.json`, `dataset_intelligence.json`, `_manifest.json`. The offline
research app (V1-P8) reads exactly these.

See [`docs/V1_P7_OFFLINE_INFERENCE.md`](./docs/V1_P7_OFFLINE_INFERENCE.md).
