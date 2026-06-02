# EDF / EDF+ Ingestion (V1-P1)

The data foundation reads EDF and EDF+ with a **pure-Python reader** (standard
library + NumPy only). There is **no third-party EDF dependency anywhere in V1** —
parsing behaviour is fully owned, auditable, and reproducible (AP-3/AP-6).

## Why a hand-written reader
- **Determinism & auditability.** We control every byte-level decision; nothing is
  hidden behind an opaque library version.
- **Minimal dependency surface.** Fewer pins to manage for a decade-lived platform.
- **Testability.** A matching fixture *writer* (test-only) lets the reader be
  tested against bytes this repository fully controls.

This choice is recorded as a governance decision (see `.gcc/decisions/`).

## What the reader decodes
- **Main header (256 bytes):** version, patient & recording identification, start
  date/time, header size, reserved (EDF+C/EDF+D), number of data records, record
  duration, signal count.
- **Per-signal headers (256 bytes each):** label, transducer, physical dimension,
  physical/digital min & max, prefiltering, samples-per-record.
- **Data records:** interleaved 16-bit little-endian integers, de-interleaved per
  signal and linearly calibrated to physical units (`float64`).
- **EDF+ annotations:** Time-stamped Annotation Lists (TALs) parsed from the
  `EDF Annotations` channel, including per-record onsets (EDF+D time-keeping).

## Calibration
Physical values use the standard EDF linear mapping:

```
physical = (digital − digital_min) × (physical_max − physical_min)
           / (digital_max − digital_min) + physical_min
```

A degenerate digital range (`digital_max == digital_min`) yields gain `1.0` and is
flagged by validation (`DEGENERATE_DIGITAL_RANGE`) rather than crashing.

## What the reader does NOT do
- It performs **no signal processing** — no filtering, resampling, montage changes,
  or normalization. Those belong exclusively to `preprocessing/` (the DSP leaf).
  The reader only decodes what the file contains.
- It does not load datasets, train models, or serve clients (boundary rules).

## Robustness
- Tolerant ASCII (latin-1) header decoding (never raises on non-strict bytes).
- `num_data_records == -1` (unknown, allowed by EDF) is resolved from file size.
- Truncated/garbled headers raise a typed `EdfReadError` with a stable `code`,
  which the pipeline turns into a structured validation issue.

## Integrity verification
`verify_integrity` recomputes the expected file size from the header
(`header_bytes + num_data_records × record_size_bytes`) and compares it to the
actual size, reporting truncation/corruption as evidence (`IntegrityResult`).
