# Determinism, Versioning & Reproducibility (V1-P2)

The DSP layer is the platform's reproducibility anchor (everything above inherits
it). This document explains the guarantees and how they are enforced.

## Determinism (AP-3 / NR-9)
- No randomness on any path; no wall-clock reads (timestamps are caller-supplied
  provenance only).
- All operations are deterministic functions of their inputs:
  - Filtering: fixed Butterworth/notch coefficients + `sosfiltfilt`.
  - Resampling: `resample_poly` with an exact rational up/down ratio.
  - Normalization: closed-form per-channel statistics.
  - Windowing: window count/boundaries are an exact function of length, rate,
    window size, overlap, and boundary policy.
- Enforced by `tests/test_determinism.py` (byte-identical outputs across runs) and
  per-stage determinism tests.

## Versioning (NR-9)
- Every stage carries an operation version (`*_OP_VERSION`); every config carries a
  component version. The pipeline carries `PREPROCESSING_VERSION`.
- A version is changed only via a recorded governance decision (NR-5).

## Reproducibility (AP-6 / NR-10)
- A run is fully described by: the **input fingerprint** (`array_fingerprint` of the
  signal) + the **config fingerprint** (`PipelineConfig.config_fingerprint`).
- The `PreprocessingLineage` records input/output fingerprints, the config
  fingerprint, and an ordered list of `TransformationRecord` (each with param and
  input/output fingerprints).
- Artifacts persist a canonical `manifest.json` so a stored result can be re-checked
  later against the same input + config.

## A note on cross-machine float identity
Bit-identical floating-point results require the *same pinned environment* (NumPy
2.2.6, SciPy 1.15.3, same CPU architecture). Within a pinned environment — which the
repository fixes via `requirements-lock.txt` — outputs are reproducible. Fingerprint
comparisons in tests run within one environment and assert exact equality.
