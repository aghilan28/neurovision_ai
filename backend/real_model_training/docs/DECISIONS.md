# Real Model Training & Benchmark — Decisions (Track 2)

Canonical record: [`ADR-0031`](../../../.gcc/decisions/ADR-0031-track2-real-model-training.md).

- **New sibling subsystem, no new architecture.** `real_model_training` orchestrates the
  governed real-training program; the five architectures + the train/evaluate/benchmark/compare
  engines are **reused** from `production_models` / `model_foundation`.
- **Real windowed data (no synthetic).** Real `[C,T]` signal via MNE (guarded by
  `eeg_foundation`), windowed, labelled by overlap with the **real** Track-1 seizure intervals,
  reduced to a deterministic feature vector, balanced, and split (patient-disjoint or stratified).
- **The reuse constraint.** The five models are feature-projection + softmax (2D `X[N,F]`), not
  raw `[C,T]` conv nets — so each window is reduced to a feature vector before training. Reusing
  them as-is is preferred over adding a new architecture layer (which the directive forbids).
- **`READY_FOR_SERVING`** extends the readiness vocabulary; it gates on evidence completeness +
  integrity + reproducibility (training + evaluation + benchmark + validation + registry + audit
  + lineage), not on a tuned accuracy target.
- **Shared lineage + audit.** Dataset → Recording → Feature Asset → Training Run → Model →
  Evaluation → Benchmark → Readiness Assessment, on the single `ml.lineage` tracker + the shared
  `ImmutableAuditLog`; the dataset node parents the Track-1 dataset node (reaches the source).
- **Determinism.** Content-addressed ids; reproducibility verified; timings informational and
  excluded from signatures + deterministic reports.
- **Scope (NR-13).** No serving / persistence / security / frontend / deployment / operations /
  Track-1 changes.
- **Honesty (NR-2).** Metrics are evidence about untuned reference architectures on a real
  single-subject cohort — not a clinical-performance claim and not external clinical validation.
