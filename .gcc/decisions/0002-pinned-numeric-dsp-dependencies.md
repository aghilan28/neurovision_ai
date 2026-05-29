# DR-0002 · Pin NumPy/SciPy as the only numeric/DSP dependencies

- **Status:** Accepted · **Phase:** V1-P1 / V1-P2 · **Date:** caller-supplied

## Context
The DSP foundation needs reliable, well-tested signal processing (filter design,
polyphase resampling) and array math. `IMPORT_RULES.md` permits `preprocessing` to
use *pinned third-party numeric/DSP libraries*. Reproducibility (NR-10) requires a
pinned environment.

## Decision
Use **NumPy 2.2.6** and **SciPy 1.15.3** as the only third-party runtime libraries,
pinned in `requirements.txt` with a fully-resolved `requirements-lock.txt`, on
CPython 3.11. `pytest 8.3.5` is a test-only dependency.

## Alternatives considered
1. **Hand-roll all DSP** (no SciPy) — maximizes ownership but re-implements
   well-validated algorithms (Butterworth design, polyphase resampling), increasing
   the risk of scientific error. Rejected: scientific validity > ownership here.
2. **Add more libraries** (e.g. `mne`, `pandas`) — unnecessary surface for V1.
   Rejected by default-deny.

## Consequences
- Deterministic, well-tested DSP within a pinned environment.
- Bit-identical results require the same pinned environment (documented in
  `preprocessing/docs/DETERMINISM.md`).

## Rules / principles invoked
AP-3, AP-6, NR-9, NR-10; `IMPORT_RULES.md` (Rule D — pinned numeric/DSP libs only).
