# V1-P7 — Offline Inference Platform (design & contracts)

> **Phase:** V1-P7 · **Status:** Implemented (offline)
> **Decision record:** [`../../../.gcc/decisions/ADR-0002`](../../../.gcc/decisions/ADR-0002-v1-p7-p8-offline-inference-and-research-app.md)

---

## 1. Determinism model

* **Content-addressed ids.** `inference_id`, lineage ids, and the execution
  *content signature* are sha256 hashes of canonical content. They **exclude**
  wall-clock timing.
* **Timing is non-hashed.** `RealClock`/`FakeClock` record durations as metadata
  only. `FakeClock` makes timing deterministic for tests.
* **Result:** identical `PipelineConfig` ⇒ identical `inference_id`, identical
  artifact checksums, identical rendered HTML.

## 2. Stage contracts

Each stage returns a record dict with a `signature`. The engine stores per-stage
status, duration (non-hashed), and signature. Stages:

1. **Dataset Ingestion** — obtain the `EEGDataset` (synthetic source in V1; real
   EEG attaches at the same contract later).
2. **Validation** — build + assert the patient-disjoint split (NR-3); dataset
   quality gate.
3. **Preprocessing** — deterministic `transform` of all windows.
4. **Dataset Intelligence** — profiles/quality/leakage/readiness (V1-P3 surface).
5. **Evaluation Preparation** — slice into patient-disjoint train/cal/test.
6. **Model Selection** — build + train a baseline via the governed `Trainer`
   (registers the model, records training lineage).
7. **Inference** — raw probabilities + logits on the inference (test) set.
8. **Calibration** — temperature scaling on the calibration set.
9. **Conformal Prediction** — split-conformal sets (coverage guarantee).
10. **Coverage Validation** — observed vs target, drift, violations.
11. **Risk Assessment** — risk scores, bands, abstain/escalate.
12. **Output Generation** — patient-disjoint evaluation + the 10 output contracts.
13. **Artifact Registration** — persist contracts + benchmark; checksums.
14. **Lineage Registration** — evaluation/uncertainty/inference lineage nodes.
15. **Audit Generation** — inference id, registry record, 7-check validation,
    reports, audit record.

## 3. Output contracts (`schemas/outputs.py`)

Prediction · Probability · Calibration · Conformal · Coverage · Risk · **Clinical**
(per-window fused record with calibrated confidence + conformal set + risk/abstain —
never a bare label, NR-4) · Summary · Report · Artifact. All typed, versioned,
canonical-JSON serializable.

## 4. Governance

* **Inference registry** — every inference registered with full version coordinates;
  silent overwrite rejected.
* **Artifacts** — deterministic, sha256-checksummed; `verify_directory` re-checks an
  on-disk run for tampering.
* **Lineage** — content-addressed; `verify_chain` proves the inference traces back
  through uncertainty → evaluation → model training.
* **Validation** — version/artifact/lineage/calibration/coverage/output/audit
  integrity (7 checks); failure is stop-and-remediate.

## 5. Jobs

`InferenceJob`, `BatchJob` (recoverable; skips completed items), `ValidationJob`,
`AuditJob`, `ArtifactJob`, `ReportJob`. `JobRunner` records results with content
signatures and supports retry/recovery.

## 6. Boundary

`backend ↛ frontend`; `ml ↛ evaluation` preserved via the `EvaluationPort`
inversion. The orchestrator composes domain modules; it implements no DSP/model/
metric logic itself.
