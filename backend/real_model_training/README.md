# Real Model Training & Benchmark (`backend/real_model_training`) — Track 2

Closes the Production Reality Audit blocker **NO MEANINGFUL TRAINED MODELS.** It turns the
**real datasets** acquired by Track 1 into **real trained models**: it windows the real
recordings into labelled samples, **trains the platform's five architectures** on that real
data, **evaluates + benchmarks + compares** them, and scores **serving readiness**.

It **trains / evaluates / benchmarks / compares / scores** models — and nothing more. It does
not serve, persist, secure, deploy, or modify Track 1, and it adds **no new architecture**.

## What it does (and does not)

* **Does:** load the real `[channels, samples]` signal from the actual file (MNE, guarded by
  the `eeg_foundation` parser); window it; label each window seizure/background by overlap with
  the **real** Track-1 seizure intervals; reduce each window to a deterministic feature vector;
  balance + analyse classes; build a patient-disjoint or class-stratified split; train EEGNet /
  DeepConvNet / Temporal CNN / Transformer EEG / Hybrid EEG (reusing the existing engines);
  evaluate (incl. sensitivity + specificity); benchmark; compare; track lineage + audit; score
  `NOT_READY` / `PARTIALLY_READY` / `READY_FOR_SERVING`; emit deterministic reports.
* **Does not:** serve, persist, secure, deploy, change operations/frontend, modify Track 1, or
  add/duplicate any model architecture. No synthetic training.

## Pipeline (T2-A … T2-L)

```
real datasets (Track 1)
  -> window into labelled samples   # data/ (real signal via MNE; labels from real intervals)
  -> train 5 architectures          # training/ (reuses production_models.train_production)
  -> evaluate                       # evaluation/ (reuses foundation + production evaluators; +sens/spec)
  -> benchmark                      # benchmarking/ (reuses production_models.benchmark_model)
  -> track experiment               # experiments/
  -> compare                        # comparison/ (reuses production_models.compare_models)
  -> lineage + registry + audit     # lineage/ + registry/ + audit/ (shared systems, no parallel)
  -> score serving readiness        # readiness/ (NOT_READY / PARTIALLY_READY / READY_FOR_SERVING)
  -> reports                        # reports/ (9 deterministic reports)
```

## Lineage (required chain)

```
Dataset -> Recording -> Feature Asset -> Training Run -> Model -> Evaluation ->
Benchmark -> Readiness Assessment
```

The Track-2 dataset node parents the **Track-1** dataset node, so one `verify_chain` from a
readiness node reaches the original dataset source (and the patient). Audit is the shared
hash-chained `ImmutableAuditLog`; lineage is the single `ml.lineage` tracker — no parallel
systems.

## Serving readiness

`READY_FOR_SERVING` requires: trained on real data + evaluated + benchmarked + registered +
audited + traceable **and** content validation passes. It gates on *evidence completeness +
integrity + reproducibility*, not on an accuracy target (the reference architectures are
untuned — NR-2).

## The reuse constraint (honest)

The five named architectures live in `production_models`/`model_foundation` and are
feature-projection + softmax models that train on a 2D feature matrix `X[N,F]` — they do not
perform raw `[channels, time]` convolution. To reuse them with **no new architecture**, each
real window is reduced to a deterministic per-channel band-power + temporal feature vector
before training. This is the binding constraint of reusing the existing models (ADR-0031),
documented rather than worked around.

## Run it

```bash
# train + benchmark + score from the real CHB-MIT corpus (the 15 criteria)
python -m scripts.verify_track2_real_models          # NV_TRACK1_NO_DOWNLOAD=1 forbids network

# tests (network-free; committed real EDF fixtures laid out as CHB-MIT)
python -m pytest tests/test_real_model_training.py tests/test_real_model_training_e2e.py
```

## Boundary & determinism

Imports `ml` + sibling `backend` (`dataset_acquisition`, `production_models`,
`model_foundation`, `eeg_foundation`, `clinical_cases.audit`) only — never `frontend`
(enforced by `tests/test_boundaries.py`). Ids/fingerprints are content-addressed;
reproducibility is verified (train twice, compare fingerprints); deterministic metrics are
hashed while wall-clock timings are informational and excluded from signatures and reports.

See [`docs/DESIGN.md`](./docs/DESIGN.md) and [`docs/DECISIONS.md`](./docs/DECISIONS.md), and the
decision record [`ADR-0031`](../../.gcc/decisions/ADR-0031-track2-real-model-training.md).
