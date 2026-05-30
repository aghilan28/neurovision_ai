# Productization P3 — Feature Engineering Platform (design & contracts)

> **Phase:** Productization P3 · **Status:** Implemented
> **Decision record:** [`../../../.gcc/decisions/ADR-0016`](../../../.gcc/decisions/ADR-0016-productization-p3-feature-engineering.md)

The objective is narrow: transform a **processed EEG asset** (P2) into a **validated
immutable feature asset**, with five families of deterministic features and full
traceability — and *nothing else* (no models/inference/classification).

---

## 1. Identity model

A feature asset id is `"feature+{hash16}"`, a content hash of `(kind,
identity_version, {processed_id, feature_key})` where `feature_key` is a fingerprint
of all feature-vector fingerprints + the extraction config. The same processed signal
with the same config always yields the same `feature_asset_id` (idempotent),
content-derived, never filename-derived. The `feature` kind is parented on `signal`.

| kind | components | parent | minted here |
|------|-----------|--------|-------------|
| feature | processed_id, feature_key | signal | yes |
| signal / eeg / case / patient | … | … | no (validated only) |

## 2. Feature engines (deterministic, P3-C…G)

* **Frequency** — Welch PSD → absolute band power (δ/θ/α/β/γ), total power, relative
  band power, band ratios (θ/α, θ/β, α/β), spectral entropy. Per channel.
* **Temporal** — mean, variance, skewness, kurtosis, RMS, zero-crossing rate, Hjorth
  activity/mobility/complexity, signal entropy. Per channel + a per-recording summary.
* **Connectivity** — pairwise coherence, phase-locking value (Hilbert), best-lag
  cross-correlation → matrices + a global synchronization summary.
* **Spectral** — PSD, spectrogram, per-band summaries, frequency histogram — stored as
  structured `FeatureVector`s (flattened values + `shape` + `axes`). No images.
* **Topography** — channel-layout model (region per channel), regional RMS groups,
  spatial summaries, topographic statistics (global field power, dispersion). No images.

## 3. Feature vectors & grouping

Every engine output is a `FeatureVector(name, family, group, scope, labels, values,
shape, axes, units)` with a content fingerprint. Scalars use a 1-element vector;
per-channel features one value per channel; matrices/tensors are flattened with
`shape`+`axes`. The service organizes vectors into `FeatureGroupRecord`s by family and
assembles the immutable `FeatureRecord` asset.

## 4. Validation (the eight checks, P3-K)

Build-time **content** checks (persisted in `FeatureValidationRecord`):
completeness (all families present, no empty vectors), integrity (finite values +
`prod(shape)==n_values`), consistency (per-channel/pair dimensions), determinism
(a second extraction reproduces identical fingerprints). Post-build **structural**
checks (`FeatureIntegrityValidator`, reusing `ml.validation.ValidationReport`):
registry, audit, lineage (chain reaches the patient), version.

## 5. Registry, audit, lineage (P3-I/J)

* **Registry** — `FeatureRegistry`: no orphan assets; re-registering a version with
  different content is a forbidden silent overwrite.
* **Audit** — reuses the shared hash-chained `ImmutableAuditLog` (`FeatureAuditRecord`);
  every extraction/validation/lineage/version/registration event is appended immutably.
* **Lineage** — reuses the shared `ml.lineage.LineageTracker`; the feature node parents
  the processed-EEG node, so `verify_chain` proves
  **Patient → Case → EEG → Processed → Feature**.

## 6. Immutability & determinism

`FeatureRecord` is a frozen dataclass; values, ids, versions, and fingerprints are
content-derived (quantized to a fixed number of decimals before hashing). The same
processed asset + config reproduces the same feature asset id, version, and signatures.

## 7. Out of scope (forbidden in P3)

Model training, model registry, inference, predictions, classification, clinical
analytics, FastAPI, database systems, authentication, frontend, deployment,
monitoring, Productization P4+, and Version 5.
