# Real Model Training & Benchmark — Design (Track 2)

## Objective

Turn the **real datasets** from Track 1 into **real trained models**: window the real
recordings into labelled samples, train the platform's five architectures on that real data,
evaluate + benchmark + compare them, and score **serving readiness** — proving at least one
production-candidate model is objectively `READY_FOR_SERVING` on actual EEG.

## Module map

| Module | Phase | Responsibility |
|---|---|---|
| `version.py` | — | version coordinates + `DETERMINISTIC_EPOCH` |
| `models/domain.py` | T2-A | closed vocabularies + records (dataset / experiment / evaluation / benchmark / comparison / readiness / candidate / registry / audit) |
| `identity/` | — | content-addressed `{kind}+{hash16}` ids |
| `data/` | T2-B | real signal loading (MNE, guarded by `eeg_foundation`), windowing, real-interval labelling, deterministic feature reduction, class balancing, splits, `DatasetBundle` assembly |
| `training/` | T2-C | trains the 5 architectures by reusing `production_models.train_production` (no new architecture) |
| `experiments/` | T2-D | experiment tracking (architecture / versions / config / hyperparameters / metrics; reproducible) |
| `evaluation/` | T2-E | reuses foundation + production evaluators; adds sensitivity + specificity |
| `benchmarking/` | T2-F | reuses `production_models.benchmark_model` (deterministic metrics hashed; timings informational) |
| `comparison/` | T2-G | reuses `production_models.compare_models` (ranking / best-per-metric / recommended) |
| `readiness/` | T2-H | serving-readiness engine (NOT_READY / PARTIALLY_READY / READY_FOR_SERVING) |
| `validation/` | — | model content validation (structured checks; the `validation_ok` gate) |
| `lineage/` | T2-I | shared `ml.lineage`; Dataset → … → Readiness Assessment, reaching the Track-1 source |
| `registry/` | T2-I | trained-model registry — no orphan records |
| `audit/` | T2-I | the shared `ImmutableAuditLog` (no parallel system) |
| `reports/` | T2-J | 9 deterministic reports |
| `schemas/` | — | a documented contract per entity |
| `service.py` | — | `RealModelTrainingService` — `prepare` / `develop` / `reports` |

## Data path (T2-B)

`data.build_real_training_dataset` reads each real recording's `[C, T]` array via MNE (the
library the platform already depends on), windows it at a fixed length/stride, and labels each
window `seizure` (1) iff it overlaps a **real** Track-1 seizure interval, else `background` (0).
Each window is reduced to a deterministic feature vector — per-channel relative band powers
(δ/θ/α/β/γ), log total power, std, RMS, line length, zero-crossing rate — then the windows are
class-balanced (keep all seizure, deterministic background subset) and split patient-disjoint
(≥3 patients) or class-stratified (single subject). The result is a `model_foundation.DatasetBundle`
(`.X` 2D, `.y`, `.split_indices`, `.record.dataset_id`) so every reused engine consumes it
unchanged.

## Reuse (no parallel systems, no new architecture)

The five architectures and the train/evaluate/benchmark/compare engines are **reused** from
`backend.production_models` + `backend.model_foundation`. Track 2 supplies the real dataset
bundle and orchestrates the governed program around them, sharing the single `ml.lineage`
tracker + the shared `ImmutableAuditLog`. Real recordings + labels come from the Track-1
`RealDatasetService`.

## Determinism

Ids/fingerprints are content-addressed. The production trainer trains twice and compares
parameter fingerprints (`reproducible`). Deterministic benchmark metrics enter every signature;
wall-clock performance (latency / memory / train / inference time) is informational and excluded
from signatures **and** from the deterministic reports (the benchmark report lists the names of
the performance measures tracked, not their volatile values). So verdicts + reports reproduce
bit-for-bit while timings are still measured.

## Test strategy

* **Network-free** unit + e2e tests lay out the committed real EDF fixtures as a CHB-MIT dataset
  (real EDF bytes + a real-format seizure summary) and run the full program on genuine files.
* A **real-corpus** test runs over the locally-acquired PhysioNet recordings when available.
