# ADR-0031 — Track 2: Real Model Training & Benchmark Program

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Product Completion Program — Track 2 (Real Model Training & Benchmark)
> **Builds on:** ADR-0001 … ADR-0030 (Productization P1–P10 + DRP-1…DRP-6 + Track 1)
> **Resolves:** Production Reality Audit blocker — *NO MEANINGFUL TRAINED MODELS*
> (models were reference-grade; insufficient training/benchmark evidence on real data)
> **Enforces / honors:** AP-6/NR-9/NR-10 (determinism), AP-5/AP-8/NR-11 (traceability),
> AP-7/NR-8 (boundaries), NR-6 (reuse, no parallel systems / no new architecture),
> AP-9/NR-5 (this record), NR-13 (scope), NR-2 (honesty)

## 1. Context

Track 1 (ADR-0030) made **real datasets** available locally (real CHB-MIT recordings + real
seizure labels, `READY_FOR_TRAINING`). The audit's next blocker is *no meaningful trained
models*: the platform's architectures were reference-grade with insufficient training and
benchmark evidence on real data.

Track 2 closes that blocker by turning the real datasets into **real trained models**:
window the real recordings into labelled samples, train the platform's five architectures on
that real data, evaluate + benchmark + compare them, and score **serving readiness**. Scope
is strictly training + benchmarking — no serving, persistence, security, frontend,
deployment, operations, or Track-1 changes (NR-13), and **no new architecture layer**.

## 2. Decisions

### D1 — A new governed `backend/real_model_training` subsystem (no new architecture)
It mirrors the platform subsystem shape (models, identity, data, training, evaluation,
benchmarking, experiments, comparison, readiness, validation, registry, audit, lineage,
reports, schemas, service). As a `backend` package it obeys the import DAG (imports `ml` +
sibling `backend`, never `frontend`; enforced by `tests/test_boundaries.py`).

### D2 — Real windowed training data from Track 1 (T2-B)
`data/` loads the **real** `[n_channels, n_samples]` signal from the actual file via MNE (the
same library the platform uses), guarded by the `eeg_foundation` parser; windows it into
fixed-length epochs; labels each window seizure/background by **overlap with the real seizure
intervals** from Track 1; reduces each window to a deterministic feature vector (per-channel
relative band powers + temporal statistics, pure NumPy); balances + analyses the class
distribution; and builds a patient-disjoint split (≥3 patients) or a class-stratified window
split (single subject). **No synthetic data.**

### D3 — Reuse the existing training/evaluation/benchmark engines (NR-6)
The five named architectures live only in `backend.production_models` /
`backend.model_foundation` and train on a 2D feature matrix `X[N,F]` via `.fit(X, y)`. Track 2
assembles a `model_foundation.DatasetBundle` from the real windows and drives the **existing**
`train_production` → foundation `evaluate` → `benchmark_model` → `build_model_evaluation` →
`compare_models` engines for `eegnet`/`deepconvnet`/`temporal_cnn`/`transformer_eeg`/
`hybrid_eeg`. No architecture code is added or duplicated. Sensitivity + specificity are
derived from the confusion matrix on top of the reused metrics.

### D4 — `READY_FOR_SERVING` readiness (T2-H)
A new classification: **NOT_READY < PARTIALLY_READY < READY_FOR_SERVING**, scored over seven
weighted dimensions (training / evaluation / benchmark / validation / registry / audit /
lineage). `READY_FOR_SERVING` requires the model to be trained on real data, evaluated, and
benchmarked, **and** registered + audited + traceable **and** content-validation-passing —
i.e. complete, reproducible, objective evidence to put it behind a serving boundary.
Readiness gates on *evidence completeness + integrity*, not an accuracy target (the reference
baselines are untuned — NR-2).

### D5 — Reuse the shared lineage + audit (T2-I; no parallel systems)
All nodes are recorded in the single `ml.lineage.LineageTracker`; events on the shared
hash-chained `ImmutableAuditLog`. The Track-2 dataset node parents the **Track-1** dataset
node, realizing **Dataset → Recording → Feature Asset → Training Run → Model → Evaluation →
Benchmark → Readiness Assessment**, so one `verify_chain` from a readiness node reaches the
original dataset source (and the patient).

### D6 — Determinism (NR-9/NR-10)
Ids/fingerprints are content-addressed; the production trainer trains twice and compares
parameter fingerprints (reproducibility verified). Deterministic benchmark metrics enter
every signature; wall-clock performance (latency / memory / train / inference time) is
informational and excluded from every signature **and from the deterministic reports** — so
verdicts and reports reproduce bit-for-bit while timings are still measured.

## 3. Consequences

- `python -m scripts.verify_track2_real_models` → **ALL 15 CRITERIA PASS** against the **real,
  locally-acquired CHB-MIT corpus**. Proof: 50 real windows (40 background / 10 seizure) from
  two genuine 1-hour 256 Hz / 23-channel recordings; all five architectures trained
  (reproducible), evaluated (incl. sensitivity/specificity), benchmarked, compared; **5/5
  READY_FOR_SERVING**; lineage chain verified to the dataset source; audit verified; registry
  orphan-free. The recommended model is `hybrid_eeg`.
- New suite adds **22 tests**; full repository suite **989 passed** (was 967). Tests run
  **network-free** by laying out the committed real EDF fixtures as a CHB-MIT dataset; a
  real-corpus test runs over the genuine PhysioNet recordings when available.
- `ruff` clean on all new code; `tests/test_boundaries.py` green; prior verify scripts (Track 1,
  DRP-1…DRP-6, productization) unaffected. No new runtime dependencies.
- A CLI (`python -m scripts.verify_track2_real_models`) trains + benchmarks + scores from the
  real corpus end to end.

## 4. Scope guard (explicitly NOT built — NR-13)

Serving, persistence, security, frontend, deployment, operations, Track-1 changes, and any
new model-architecture layer. Track 2 trains, evaluates, benchmarks, compares, and scores
models — **only**.

## 5. Honesty statement (NR-2)

Track 2 delivers **real** trained models with **real, objective, reproducible** evidence on
**real EEG** (CHB-MIT). The reported accuracies/ROC-AUC are **evidence about the platform's
untuned reference architectures on a single-subject real cohort windowed into a balanced
sample set** — they are *evidence about those baselines*, **not** a clinical-performance
claim and **not** external clinical validation. Because the five reused architectures are
feature-projection + softmax models, each real window is reduced to a deterministic feature
vector before training (the binding constraint of reusing the existing models — they do not
perform raw `[C,T]` convolution); this is documented rather than worked around with a new
architecture. The proof corpus is a single subject (chb01, the minimal verifiable subset);
more subjects/corpora flow through the same governed program. `READY_FOR_SERVING` certifies
*evidence completeness + integrity + reproducibility*, not tuned clinical accuracy. This
closes the *no meaningful trained models* blocker: NeuroVision can now train, evaluate,
benchmark, compare, trace, and score the serving readiness of models on **actual EEG
recordings** rather than synthetic fixtures.
