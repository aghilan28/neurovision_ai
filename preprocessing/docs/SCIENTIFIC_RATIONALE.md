# Scientific Rationale (V1-P2 defaults)

Every default DSP choice is documented here so it can be reviewed by a domain
expert and changed only via a recorded governance decision (NR-5). No arbitrary
DSP is performed.

## Resampling — target 256 Hz, polyphase, anti-aliased
- 256 Hz is a power-of-two rate comfortably above twice the highest
  clinically-relevant EEG frequency (~70 Hz), leaving headroom for the anti-alias
  transition band.
- SciPy `resample_poly` uses an FIR polyphase prototype that **inherently
  anti-aliases**; the up/down ratio is the exact rational approximation of
  `target/original`, so the operation is deterministic.

## Filtering — bandpass 0.5–70 Hz, notch at mains, zero-phase
- **0.5 Hz high-pass** removes slow baseline drift (electrode/sweat/movement)
  while preserving clinically-relevant slow activity.
- **70 Hz low-pass** limits high-frequency/EMG contamination while retaining
  activity up to the high-gamma-adjacent range used in critical-care EEG.
- **Butterworth, order 4** — maximally flat passband, no ripple.
- **Zero-phase application** (`sosfiltfilt`, forward-backward) avoids phase
  distortion of waveform morphology (important clinically). It squares the
  magnitude response, so the *effective* attenuation is stronger than the single-
  pass design that `frequency-response validation` checks.
- **Notch (default 60 Hz, Q=30)** removes mains interference; the mains frequency
  is configurable (50 Hz regions). Notches at/above Nyquist are skipped.

## Montage — referential / average-reference / bipolar
- **Referential (identity)** is the default no-op: many recordings are already
  referential, and re-referencing is an explicit, opt-in choice.
- **Average reference (CAR)** subtracts the across-channel mean — a standard
  re-reference that reduces common-mode noise.
- **Longitudinal bipolar ("double banana")** is the standard clinical bipolar
  montage; derivations are `anode − cathode` over canonical 10-20 electrodes, with
  10-20↔10-10 alias resolution (T3↔T7, etc.). Missing channels are handled
  explicitly (report vs. abort) — never fabricated.

## Normalization — per-channel z-score (default)
- Standardizes inter-channel amplitude scale, a known EEG nuisance, **without
  leaking across windows** (per-recording statistics). Robust (median/IQR) is
  available for heavy-tailed/artifact-prone data. `none` disables it.
- A small epsilon guards against division by zero on flat channels.

## Windowing — 10 s, non-overlapping (default)
- 10 s windows are a common analysis unit for ICU continuous EEG. Overlap and a
  pad/drop boundary policy are configurable. The trailing partial window is dropped
  by default so every window has identical length.

> All of the above are **defaults**, fully overridable via `PipelineConfig`, and
> every choice is captured in the run's `config_fingerprint` and lineage.
