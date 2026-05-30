# Productization P2 — Signal Processing Foundation (design & contracts)

> **Phase:** Productization P2 · **Status:** Implemented
> **Decision record:** [`../../../.gcc/decisions/ADR-0015`](../../../.gcc/decisions/ADR-0015-productization-p2-signal-processing.md)

The objective is narrow: transform a **raw EEG asset** (P1) into a **validated clean
EEG asset**, with quality assessment, artifact detection/removal, deterministic
filtering, and full traceability — and *nothing else* (no AI/inference/classification).

---

## 1. Identity model

A processed asset id is `"signal+{hash16}"`, a content hash of `(kind,
identity_version, {eeg_asset_id, processing_key})` where `processing_key` is a
fingerprint of the raw signal + the ordered pipeline. The same raw recording cleaned
with the same pipeline always yields the same `processed_id` (idempotent), and the id
is content-derived, never filename-derived. The `signal` kind is parented on `eeg`.

| kind | components | parent | minted here |
|------|-----------|--------|-------------|
| signal | eeg_asset_id, processing_key | eeg | yes |
| eeg / case / patient | … | … | no (validated only) |

## 2. Filtering (P2-C, deterministic)

`FilteringEngine` uses `scipy.signal` (zero-phase Butterworth via `sosfiltfilt`, IIR
`iirnotch`) so filters are deterministic and stable on short recordings:
bandpass / highpass / lowpass / notch / **reference correction** (average). Each
operation returns a *new* array (inputs never mutated) plus a tracked `FilterConfig`.

## 3. Quality (P2-D, deterministic)

`SignalQualityEngine` computes, per channel: noise level (normalized HF energy),
flatness, saturation fraction, completeness (finite fraction), stability (windowed-RMS
consistency), and a combined quality score; and per recording: quality score, noise,
stability, completeness, sampling consistency, a `QualityGrade` band, structured
findings (with severity), and recommendations. It is a pure function of the signal.

## 4. Artifact detection (P2-E)

`ArtifactDetectionEngine` emits a structured `SignalArtifactRecord` (type, severity,
confidence, affected channels, onset, affected duration) for each of: eye-blink, EMG,
movement, powerline, channel dropout, flat channel, saturated channel. Detectors are
specific (amplitude statistics for structural problems, robust z-score for transient
biological/movement artifacts, band-power ratios for oscillatory artifacts), so a
clean, stationary recording yields no false positives.

## 5. Artifact removal (P2-F, deterministic, non-destructive)

`ArtifactRemovalEngine` implements ICA-based removal (a self-contained, fixed-init
FastICA — reproducible, no randomness, no extra dependency; drops components
correlated with frontal/ocular activity), adaptive filtering (least-squares EOG
regression), interpolation (temporal repair of non-finite samples), channel repair
(spatial repair from good channels), and noise suppression (notch + bandpass). Every
method returns a new array and never mutates its input.

## 6. Processing pipeline & the processed asset (P2-G)

`ProcessingPipeline` composes the engines into one ordered, fully-tracked
transformation. Each step records its before/after array fingerprint, so the
transformation is a contiguous, verifiable chain from raw to processed. The
`ProcessedEEGRecord` aggregate references the raw + processed `SignalRecord`
descriptors, the `SignalQualityRecord`, the detected artifacts, the
`SignalProcessingRecord`, the `ProcessingHistory` / `ArtifactHistory` /
`QualityHistory`, the processed-signal storage reference, normalized metadata, status,
version, lineage node, and audit head. It carries no raw signal array.

## 7. Storage, registry, audit, lineage (P2-H/I)

* **Storage** — `ProcessedSignalStore` writes the cleaned signal (deterministic,
  quantized C-order float64 bytes) to a content-addressed local store with checksum +
  fingerprint + integrity `verify`. The raw store is never written to.
* **Registry** — `SignalRegistry`: no processed asset exists outside it; re-registering
  a version with different content is a forbidden silent overwrite.
* **Audit** — reuses the shared hash-chained `ImmutableAuditLog` (`SignalAuditRecord`);
  every load/quality/detection/processing/storage/lineage/version/registration event
  is appended immutably.
* **Lineage** — reuses the shared `ml.lineage.LineageTracker`; the processed node
  parents the raw EEG node, so `verify_chain` proves **Patient → Case → EEG → Processed**.

## 8. Integrity (the two cardinal invariants)

`SignalIntegrityValidator` (reusing `ml.validation.ValidationReport`) checks identity,
registry, storage, quality, processing traceability (the step fingerprint chain is
contiguous, raw → processed), artifacts, audit, lineage (reaches the patient), version
— plus **raw EEG immutability** (the P1 raw bytes still verify) and **processing
traceability**.

## 9. Out of scope (forbidden in P2)

Feature extraction, model training, inference, predictions, classification, clinical
analytics, FastAPI, database systems, authentication, frontend, deployment,
monitoring, Productization P3+, and Version 5.
