# DR-0006 · Default DSP parameters

- **Status:** Accepted · **Phase:** V1-P2 · **Date:** caller-supplied

## Context
The pipeline needs sensible, documented defaults for critical-care EEG. NR-9
requires determinism; "no arbitrary DSP" — every choice must be justified.

## Decision
Defaults (all overridable via `PipelineConfig`, all captured in
`config_fingerprint`): resample to **256 Hz** (polyphase, anti-aliased); bandpass
**0.5–70 Hz** Butterworth order 4, zero-phase; notch **60 Hz** (Q=30), zero-phase;
montage **referential identity** (re-reference/CAR/bipolar opt-in); normalization
**per-channel z-score over the recording**; windows **10 s non-overlapping, drop
trailing partial**. Full rationale: `preprocessing/docs/SCIENTIFIC_RATIONALE.md`.

## Alternatives considered
- Other rates (250/200 Hz), bands (1–40 Hz), 50 Hz mains, per-window normalization,
  overlapping windows — all are *configurable*; the defaults reflect common ICU cEEG
  practice and the platform's reproducibility-first stance. Mains frequency is
  region-dependent and intentionally configurable.

## Consequences
- Reasonable, reproducible out-of-the-box behaviour; every choice is recorded.
- Changing a default is a governance event (NR-5) and changes the fingerprint.

## Rules / principles invoked
AP-3, AP-6, NR-9, NR-10, NR-13 (no arbitrary/out-of-scope DSP), NR-5.
