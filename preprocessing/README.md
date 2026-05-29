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
