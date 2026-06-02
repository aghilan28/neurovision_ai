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

## Items explicitly **not** debt (by design, recorded for clarity)

- **Canonical-helper duplication** between `datasets/_canonical.py` and
  `preprocessing/_canonical.py` is a *deliberate* design choice to keep
  `preprocessing` a pure leaf (see [DR-0003](../decisions/0003-preprocessing-owns-its-input-contract.md)),
  not debt. Unifying it would require a new shared leaf module and a governance
  decision; it is intentionally avoided in V1.
- **Documented extension points** (future formats, montages, normalization,
  streaming) are *out-of-scope deferrals* (NR-13), not debt — see the
  `EXTENSION_POINTS.md` docs in each module.
- **EDF+D discontinuity** is *read* (record onsets recovered) but not yet used to
  re-time annotations; this is a scope boundary for V1, documented in
  `datasets/docs/EDF_INGESTION.md`, not a hidden shortcut.
