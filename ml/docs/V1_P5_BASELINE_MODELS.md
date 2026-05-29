# V1-P5 — Baseline Model Layer (design & model cards)

> **Phase:** V1-P5 · **Status:** Implemented
> **Decision record:** [`../../.gcc/decisions/ADR-0001-...`](../../.gcc/decisions/ADR-0001-v1-p5-p6-baseline-models-and-uncertainty.md)

This document is the design reference and model-card collection for the V1 baseline
models. The goal of these baselines is **reliability, reproducibility,
auditability, and uncertainty-readiness — not peak accuracy**. Every future
architecture (deep TCN, Mamba, foundation models) is compared against them through
the same evaluation + benchmark path.

---

## 1. Subsystem map (`ml/`)

```
ml/
├── schemas/        typed, versioned model I/O contracts
├── models/         SimpleCNN · EEGNet · TCN + factory (the only constructor)
├── data/           ML dataset adapter (the directive's "ml/datasets")
├── training/       deterministic training pipeline, config, manifest, report
├── validation/     the 7 mandated training-validation checks
├── registry/       the model registry (no model exists outside it)
├── artifacts/      checksummed, deterministic artifact store
├── lineage/        version bundles + content-addressed lineage graph
├── benchmarking/   benchmark records + registry; EvaluationPort (no eval import)
├── uncertainty/    V1-P6 (see ml/uncertainty/README.md)
├── provenance.py   hashing / content-addressing / canonical JSON IO
└── version.py      all version constants
```

## 2. Model contract (shared by every architecture)

* **Input contract** — `InputBatch`: float `(N, C, T)` produced by deterministic
  preprocessing (carries `preprocessing_version`).
* **Output contract** — `ProbabilityOutput (N,K)` + `ClassOutput (N,)` +
  `MetadataOutput` (full provenance) + `UncertaintyPlaceholder` (filled by V1-P6) +
  optional `ConformalOutput`. A `Prediction` is *clinically complete* only when
  calibrated uncertainty is attached (NR-4).
* **Config schema** — `ModelConfig{name, n_channels, n_samples, n_classes, seed,
  params}`; each architecture validates its own `params`.
* **Architecture spec / version / lineage metadata** — `model.architecture_spec()`
  returns layers + input/output contracts + config schema + versions.

Common design: a **deterministic, seeded feature extractor** (fixed weights) +
a **trained multinomial-logistic (softmax) head** (deterministic full-batch
gradient descent). This is framework-free, CPU-only, and bit-for-bit reproducible.

## 3. Model cards

### SimpleCNN (`simple_cnn@1.0.0`)
- **Architecture:** Conv1D(time) → ReLU → AvgPool → Conv1D(time) → ReLU →
  GlobalStatsPool(mean+std) → standardize → softmax head.
- **Role:** the plain temporal-CNN reference / performance floor.
- **Inductive bias:** local temporal patterns + global band-power statistics.

### EEGNet (`eegnet@1.0.0`)
- **Architecture:** temporal conv (shared across channels) → depthwise **spatial**
  conv (channel mixing, depth D) → ELU → AvgPool → **separable** conv (depthwise +
  pointwise) → ELU → AvgPool → GlobalStatsPool → softmax head.
- **Role:** EEG-specific reference separating temporal and spatial filtering.
- **Inductive bias:** factorized temporal/spatial structure characteristic of EEG.

### TCN (`tcn@1.0.0`)
- **Architecture:** 1×1 input projection → stacked **dilated causal** Conv1D
  residual blocks (dilations 1,2,4) with ReLU → GlobalStatsPool → softmax head.
- **Role:** long-receptive-field temporal reference; no future leakage (causal).
- **Inductive bias:** multi-scale temporal/rhythmic structure.

All three: deterministic given `(config, seed)`; weights content-hashed
(`weights_signature`) for artifact integrity.

## 4. Training framework

`Trainer.run(...)` is the single governed path:

```
pre-training validation  → preprocess + patient-disjoint slice → deterministic fit
→ checksummed weights → reproducible model_version → version bundle
→ deterministic manifest → lineage record → register model → post-training validation
→ training report
```

**Training configuration tracked:** dataset version, split version, preprocessing
version, model version, optimizer, learning rate, batch size, epochs, random seed,
hardware metadata, environment metadata (deterministic manifest).

**The 7 training-validation checks:** dataset exists · patient-disjoint split
exists · version consistency · configuration validity · artifact integrity ·
lineage integrity · evaluation compatibility. A failing check is stop-and-remediate.

## 5. Governance: registry · artifacts · lineage · benchmarking

- **Model registry** — every model is registered with model/architecture/training/
  dataset/preprocessing/evaluation/benchmark/artifact versions, lineage id, training
  date, owner, status. No model exists outside the registry; silent overwrites with
  a different content signature are rejected.
- **Artifacts** — deterministic weights serialization (not `np.savez`, whose zip
  headers embed timestamps), every artifact sha256-checksummed; silent modification
  is detected.
- **Lineage** — content-addressed `VersionBundle` + `LineageRecord` graph;
  `verify_chain` proves no broken links. Every prediction is traceable end-to-end.
- **Benchmarking** — integrates with the evaluation framework via the
  `EvaluationPort` protocol (the ML layer never imports `evaluation`, NR-8). Each
  `BenchmarkRecord` bundles metrics · dataset · split · version bundle · lineage
  bundle · evaluation audit · benchmark id, and is reproducible. Non-patient-disjoint
  results cannot be benchmarked (NR-3).

## 6. Reproducibility

Identical config ⇒ identical model_version, weights bytes, lineage id, benchmark
id, and report checksums. Verified by tests in `tests/` (determinism,
reproducibility, boundary, patient-disjoint).
