# The Preprocessing Pipeline (V1-P2)

The pipeline transforms a `RawRecording` into a standardized `WindowSet` (or a
`ProcessedSignal` if windowing is disabled), recording every step.

```
RawRecording
   │
   ▼
[1] input validation ──fail──► (status=failed, structured evidence)
   │ ok
[2] channel validation ──fail──► (status=failed)        # only if a montage is configured
   │ ok
[3] resampling      → effective_hz (polyphase, anti-aliased)         ─┐
[4] filtering       → zero-phase bandpass + notch (+ optional detrend) │ each step
[5] montage         → referential / average-ref / bipolar             │ recorded as a
[6] normalization   → z-score / robust (per-recording)                │ TransformationRecord
[7] windowing       → fixed-length windows (+ per-window norm if set) ─┘
   │
[8] output validation  (shape-consistent, finite)
[9] quality reporting  (report-only; assessed on pre-normalization signal)
[10] lineage recording (PreprocessingLineage: input/output fingerprints, config fp)
   │
   ▼
PreprocessingResult { status, windows|processed_signal, stage_results,
                      validations, quality, lineage, filter_specs,
                      frequency_response_checks, montage_result }
```

## Stage notes

- **Each stage is independently testable** (its function lives in its own module
  and has direct unit tests) and reports a `StageResult` with status + fingerprints.
- **Order of the filter chain** is fixed and deterministic: detrend → bandpass →
  notch.
- **Quality is assessed on the post-filter/montage, pre-normalization signal** so
  amplitude-based checks (e.g. saturation, line noise) remain meaningful — z-score
  normalization would otherwise mask them. The stage is still *reported* at the
  directive's position (after output validation).
- **Normalization scope.** `per_channel_recording` (default) normalizes the 2-D
  signal before windowing. `per_channel_window` defers normalization into the
  windowing stage (each window normalized independently); the normalization stage
  is then recorded as `skipped` with a deferral note (explicit, not hidden).

## Failure behaviour
The pipeline **never raises on data problems**. A failing validation or a stage
exception (bad filter design, missing montage channels under the ERROR policy,
invalid window parameters) yields `status = "failed"` with all evidence gathered so
far — so the caller always receives structured, inspectable output.
