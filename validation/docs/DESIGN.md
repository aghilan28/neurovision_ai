# Validation & Performance Assurance — Design (Productization P9)

## Objective

Produce objective **evidence** of how well NeuroVision performs, by measuring the existing
P1–P8 systems without modifying them.

## Position

`validation/` is a top-level evaluation layer (peer of `scripts/`/`operations/`). It
composes and observes the platform; it is unconstrained by the per-module import DAG and
may import `backend`/`operations` lazily. The dependency is one-way — no domain package
imports `validation`.

## The harness

`PlatformHarness` is the single seam that *exercises* the real platform:

* `build_cohort(eeg_files)` — runs the real P1→P3 services to produce real feature assets.
* `train_models(feats, architectures)` — reuses the real P4 service to train + evaluate the
  baselines (no new training regime; the platform has no persisted weights, so a model is
  its deterministic reconstruction).
* `run_pipeline(eeg_file, mut, ...)` — runs the real P1→P5 pipeline, capturing per-stage
  success + informational latency + a deterministic output fingerprint + traceability.
* `probe_ingest(path)` — feeds an input to the real ingestion and reports whether it was
  handled gracefully (never raises).

## Deterministic vs informational

Output fingerprints, success/failure counts, metric values, and readiness scores are
**deterministic** and enter signatures. Wall-clock latency, throughput, and peak memory are
**informational** and never enter a signature — so verdicts reproduce bit-for-bit while
timings are still reported.

## Subsystems

* **benchmarking (P9-B)** — model / pipeline / inference / workflow / operational runners;
  each tracks success/failure + latency/throughput/memory + a deterministic signature.
* **performance** — validates benchmark results against deterministic thresholds
  (success-rate + determinism), not timing thresholds.
* **robustness (P9-E)** — corrupted / partial / empty / truncated / header-only / noisy /
  unsupported / nonexistent inputs; asserts graceful handling (no crash) + recovery.
* **reliability (P9-F)** — repeated / long-running / stress execution + registry / audit /
  lineage / workflow integrity; every repeat reproduces the same fingerprint.
* **reproducibility** — determinism within an instance and across independent instances.
* **calibration (P9-G)** — reads the P4 evaluation (ECE/Brier) + P5 inference confidence /
  calibration / stability and validates them (in range, finite, reported with the label).
* **drift (P9-H)** — measures input / feature / prediction / pipeline drift + model
  consistency. Measure only; no correction.
* **scorecards (P9-I)** — nine readiness scorecards with measurable boolean criteria.
* **reporting (P9-J)** — nine reports + an executive summary answering the five questions.

## Determinism caveat

Model accuracy comes from deterministic, untuned reference baselines (P4). It is reported
as evidence, never used as a readiness gate; readiness gates on correctness, determinism,
calibration validity, and traceability.

## Out of scope (forbidden in P9)

New models, model retraining (as a regime), new features, frontend/backend/operational
changes, clinical validation, pilot deployments, Version 5, Productization P10.
