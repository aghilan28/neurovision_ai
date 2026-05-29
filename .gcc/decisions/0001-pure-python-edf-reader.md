# DR-0001 · Pure-Python EDF/EDF+ reader (no third-party EDF library)

- **Status:** Accepted · **Phase:** V1-P1 · **Date:** caller-supplied (provenance)

## Context
V1-P1 must ingest EDF/EDF+ deterministically and auditably. Common libraries
(`pyedflib`, `mne`) would add a heavy, version-sensitive dependency whose byte-level
parsing behaviour we would not own.

## Decision
Implement the EDF/EDF+ reader in pure Python (standard library + NumPy) inside
`datasets/ingestion/edf_reader.py`, plus a matching test-only EDF *writer* so the
reader is exercised against bytes this repository fully controls.

## Alternatives considered
1. **`pyedflib`** — mature, but adds a C-extension dependency and cedes control of
   parsing/decisions; harder to audit and pin for a decade-lived platform.
2. **`mne`** — large, feature-rich, but far beyond ingestion needs and a heavy pin.
3. **Pure-Python reader (chosen)** — full ownership, minimal dependency surface,
   deterministic, auditable; cost is the code we must maintain and test.

## Consequences
- Full control over determinism and error reporting (typed `EdfReadError`).
- Minimal dependency surface (only NumPy for array math).
- We own correctness; mitigated by a comprehensive round-trip test suite.

## Rules / principles invoked
AP-3 (determinism), AP-6 (reproducibility), AP-12 (long-term cost), NR-9 (no hidden
nondeterminism), NR-13 (EDF/EDF+ only — other formats reported, not parsed).
