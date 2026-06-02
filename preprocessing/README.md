# `preprocessing/` — DSP Layer

> **Layer:** DSP (Digital Signal Processing) Layer
> **Directory README type:** Repository Architecture Foundation (V0-P2)
> **Status (V0):** Boundary contract defined; **no code yet** (correct for V0).
> **Governing docs:** [`../docs/ARCHITECTURAL_PRINCIPLES.md`](../docs/ARCHITECTURAL_PRINCIPLES.md) (AP-3, AP-6), [`../docs/NON_NEGOTIABLE_RULES.md`](../docs/NON_NEGOTIABLE_RULES.md) (NR-9, NR-10), [`../docs/architecture/IMPORT_RULES.md`](../docs/architecture/IMPORT_RULES.md)

The lowest layer in the dependency order and the **foundation of reproducibility**.
Preprocessing turns raw EEG into deterministic, model-ready signal
representations. **It imports nobody** within the platform.

---

## Purpose
Provide **deterministic, versioned** signal-processing transforms for EEG: the
single, authoritative path from raw recordings to clean, normalized, windowed
signal ready for downstream use.

## Responsibilities
- Deterministic filtering, resampling, montage handling, windowing/segmentation,
  and normalization of EEG.
- Artifact-aware processing primitives (Objective **S2**).
- Emit, with every output, the **preprocessing version** used (provenance for
  traceability, AP-5).
- Guarantee: *same input + same version ⇒ same output* (AP-3, NR-9).

## Allowed dependencies
- **Internal platform modules:** **none.** Preprocessing is a pure leaf.
- **Third-party numerical/DSP libraries** only (e.g. array/signal libraries),
  pinned for reproducibility.

## Forbidden dependencies
- ❌ `datasets/`, `ml/`, `evaluation/`, `backend/`, `frontend/`,
  `monitoring/`, `deployment/` — **importing any of these is forbidden** (NR-8).
- ❌ Any source of nondeterminism on the production path: unseeded randomness,
  wall-clock dependence, ordering-dependent global state (NR-9).

## Future responsibilities
- **V1:** the full deterministic offline preprocessing pipeline.
- **V3:** streaming-safe windowing/buffering that preserves determinism and does
  not introduce cross-patient leakage.

## Version ownership
- **Introduced/owned from V1** (DSP layer becomes real in V1).
- Contract defined in **V0-P2** (this README).

## Examples
- A band-pass filter with pinned coefficients producing identical output across runs.
- A montage re-referencer that maps heterogeneous input montages to a canonical form.
- A windowing function that segments a recording into fixed-length analysis windows.

## Boundary rules
- **Imports nobody** inside the platform (it sits at the bottom of the acyclic
  [dependency graph](../docs/architecture/DEPENDENCY_GRAPH.md)).
- Must be **deterministic and versioned**; nondeterminism is a rule violation (NR-9).
- Does **not** load datasets, train/run models, evaluate, or serve — those belong
  to `datasets/`, `ml/`, `evaluation/`, and `backend/` respectively.
- Consumed by `datasets/`, `ml/`, and `evaluation/`; never depends on them.


---

## Version 1 (V1-P2) — Implemented Signal-Processing Foundation

> The boundary contract above (V0-P2) is **unchanged and still authoritative**.
> This section documents the V1-P2 implementation that *populates* this module
> within those boundaries (Principle **AP-1**: extend, never rewrite).

### What V1-P2 delivers
A deterministic, versioned, traceable preprocessing pipeline that turns a raw EEG
signal representation into standardized, windowed signal — recording **every
transformation** so the result is auditable and reproducible. Downstream models
consume the standardized output and never need to know how preprocessing works
internally.

```
input validation → channel validation → resampling → filtering → montage →
normalization → window generation → output validation → quality reporting →
lineage recording
```

### Subsystem layout
| Path | Responsibility |
|------|----------------|
| [`schemas/`](./schemas) | Signal/window contracts, fingerprintable configs, reports, lineage. |
| [`resampling.py`](./resampling.py) | Deterministic anti-aliased polyphase resampling. |
| [`filters/`](./filters) | Zero-phase bandpass/notch + detrend, with frequency-response validation. |
| [`montages/`](./montages) | Referential / average-reference / bipolar montages + channel mapping. |
| [`normalization/`](./normalization) | Explicit z-score / robust normalization (per-recording or per-window). |
| [`windowing/`](./windowing) | Deterministic fixed-length window generation. |
| [`quality/`](./quality) | Report-only signal-quality detectors (never removes data). |
| [`validation/`](./validation) | Input / channel / output validation. |
| [`pipelines/`](./pipelines) | The orchestrator that composes the stages + records lineage. |
| [`artifacts/`](./artifacts) | Output persistence (`.npz` + canonical `manifest.json`) + artifact reports. |
| [`docs/`](./docs) | Pipeline, scientific rationale, determinism, and extension docs. |
| [`tests/`](./tests) | Per-stage, scientific-correctness, determinism, and boundary tests. |

### Minimal usage
```python
import numpy as np
from preprocessing.schemas import RawRecording, PipelineConfig
from preprocessing.pipelines import PreprocessingPipeline
from preprocessing.artifacts import write_artifacts

rec = RawRecording.create(signals, channel_names, sampling_rate_hz=200.0,
                          record_id="rec-1", patient_id="patient-1")

result = PreprocessingPipeline(PipelineConfig()).run(rec, expected_channels=("FP1", "CZ"))
assert result.ok
windows = result.windows.data            # (n_windows, n_channels, window_samples)
report = write_artifacts(result, "out/") # arrays + canonical manifest with lineage
```

### Determinism, versioning & traceability (AP-3/AP-6, NR-9/NR-10/NR-11)
- Every stage is **versioned** and **independently testable**; every transform is
  recorded as a `TransformationRecord` with input/output/param fingerprints.
- A run is fully described by its input fingerprint + `config_fingerprint`.
- Filters are applied **zero-phase** and their **frequency response is validated**.
- Quality is **report-only** — data is never removed or altered.

### Dependencies used (pinned)
`numpy`, `scipy` (the allowed pinned numeric/DSP libraries). **No internal imports**
— `preprocessing` is the dependency-graph leaf (NR-8), enforced by a test in
[`tests/test_boundaries.py`](./tests/test_boundaries.py).
