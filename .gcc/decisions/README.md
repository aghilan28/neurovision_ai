# `.gcc/decisions/` — Decision Records

> **Layer:** Governance & Context Control (`.gcc/`) · **Rule:** NR-5 (never change
> architecture without documentation) · **Principle:** AP-9/AP-11 (Lore Protocol).

This directory stores **consequential, versioned, dated decisions** with their
rationale and the alternatives considered — the durable *why* behind the code
(NR-5, NR-14). The constitution in `docs/` remains the source of truth; these
records explain choices made *within* it.

> **Scope note.** The automated GCC *mechanisms* (import checks, decision-record
> tooling, version gates) are owned by Phase **V0-P3** and are **not yet
> implemented** (the repository currently contains V0-P1 + V0-P2). These records
> are the decision **store** the `.gcc/` contract describes, authored as
> documentation so the rationale is preserved now (NR-5/NR-14). Mechanizing their
> enforcement remains V0-P3 work.

## Record format
Each record uses: **Context → Decision → Alternatives considered → Consequences →
Rules/Principles invoked**, plus a status and the phase that introduced it.

## Index (V1-P1 + V1-P2)
| # | Decision | Phase |
|---|----------|-------|
| [0001](./0001-pure-python-edf-reader.md) | Pure-Python EDF/EDF+ reader (no third-party EDF lib) | V1-P1 |
| [0002](./0002-pinned-numeric-dsp-dependencies.md) | Pin NumPy/SciPy as the only numeric/DSP dependencies | V1-P1/P2 |
| [0003](./0003-preprocessing-owns-its-input-contract.md) | `preprocessing` defines its own `RawRecording` input | V1-P2 |
| [0004](./0004-content-addressed-identity.md) | Content-addressed identity + order-independent fingerprints | V1-P1 |
| [0005](./0005-conservative-unknown-patient-identity.md) | Unknown patient identity ⇒ distinct patient (conservative) | V1-P1 |
| [0006](./0006-default-dsp-parameters.md) | Default DSP parameters (resample/filter/montage/normalize/window) | V1-P2 |
| [0007](./0007-quality-and-normalization-scope.md) | Quality assessed pre-normalization; per-window norm deferral | V1-P2 |
