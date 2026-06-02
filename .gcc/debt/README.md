# `.gcc/debt/` — Technical-Debt Registry

> **Rule:** NR-2 (never accept hidden technical debt) · **Budget:** V1 = *very low*,
> recorded debt only, with a repayment plan (VERSION_EVOLUTION_MODEL §7).

All acknowledged shortcuts must be recorded here with: what, why, risk, and a
repayment plan. **Undocumented debt is forbidden.**

## V1-P1 + V1-P2 ledger

**No technical debt incurred.** The EEG Data Foundation (V1-P1) and Signal-
Processing Foundation (V1-P2) were implemented without shortcuts that weaken
architecture, determinism, traceability, or boundaries.

| ID | Description | Risk | Repayment plan | Status |
|----|-------------|------|----------------|--------|
| — | (none) | — | — | — |

## V1-P3 + V1-P4 ledger

**No technical debt incurred.** The Dataset Intelligence Layer (V1-P3) and the
Evaluation Foundation (V1-P4) were implemented without shortcuts that weaken
architecture, determinism, patient-disjoint validation, traceability, or boundaries.

| ID | Description | Risk | Repayment plan | Status |
|----|-------------|------|----------------|--------|
| — | (none) | — | — | — |

## Items explicitly **not** debt (by design, recorded for clarity)

- **Per-layer canonical helpers** (`datasets`/`preprocessing`/`evaluation` each have
  a small `_canonical.py`) are a *deliberate* choice to keep `preprocessing` a pure
  leaf and each layer self-contained (see
  [DR-0008](../decisions/0008-per-layer-canonical-helpers.md) and
  [DR-0003](../decisions/0003-preprocessing-owns-its-input-contract.md)), **not**
  debt. A shared leaf module would be an architecture change requiring a governance
  decision; intentionally deferred.
- **Calibration / clinical metrics are placeholders** (registered, not computed) —
  an *out-of-scope deferral* to the future uncertainty/clinical phases (NR-13), not
  a shortcut (see [DR-0011](../decisions/0011-pure-numpy-metrics-calibration-placeholders.md)).
- **Cross-dataset / temporal splits** are documented extension points, not built
  (NR-13) — see `evaluation/docs/SPLITS_AND_LEAKAGE.md`.
- **Documented extension points** (future formats, montages, normalization,
  streaming) are *out-of-scope deferrals* (NR-13), not debt — see the
  `EXTENSION_POINTS.md` docs in each module.
- **EDF+D discontinuity** is *read* (record onsets recovered) but not yet used to
  re-time annotations; this is a scope boundary for V1, documented in
  `datasets/docs/EDF_INGESTION.md`, not a hidden shortcut.
