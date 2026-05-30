# ADR-0015 — Productization P2: Signal Processing Foundation

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Productization P2
> **Builds on:** ADR-0001 … ADR-0014 (esp. ADR-0014 — Real EEG Foundation, P1)
> **Enforces / honors:** AP-1 (vertical population, no re-layering), AP-3/AP-6/NR-9/NR-10
> (determinism/reproducibility), AP-5/AP-8/NR-11 (traceability/audit), AP-7/NR-8
> (boundaries), AP-9/NR-5 (this record), NR-6 (reuse, don't re-implement), NR-13 (scope)
> **Decision owner:** Application/platform engineering (Kiro-assisted, subject to NR-7)

Captures why the Productization P2 **Signal Processing Foundation**
(`backend/signal_processing`) is shaped as it is, so the rationale survives turnover
(NR-14).

---

## 1. Context

Productization P1 (ADR-0014) made the platform accept a **real EEG file** and store it
as a traceable raw asset. P2 takes the next narrow step: turn a **raw EEG asset** into
a **validated clean EEG asset** — quality assessment, artifact detection/removal, and
deterministic filtering — and nothing else. No AI, model training, inference,
classification, predictions, or clinical decisions.

This is **productization**, not a new version or architecture/governance expansion. It
must build strictly on P1 and reuse existing platform patterns.

## 2. Decisions

### D1 — One new `backend` subsystem, vertical population only (AP-1)
`backend/signal_processing` mirrors the established subsystem shape (models / identity
/ filtering / quality / artifacts / preprocessing / storage / registry / validation /
lineage / audit / reports / schemas / service). It imports `ml`,
`backend.eeg_foundation` types, and the shared audit primitive from
`backend.clinical_cases.audit` (intra-`backend` reuse); it never imports `frontend`
(enforced by `tests/test_boundaries.py`).

### D2 — Build on P1; never redesign or duplicate the EEG Foundation
The layer **reads** the immutable raw EEG bytes from the P1 store and references the P1
`EEGRecord`. It does not modify, replace, or re-implement P1. The processed asset's
identity is parented on the raw `eeg` id, and its lineage parents the raw EEG lineage
node, so the chain is **Patient → Case → EEG → Processed**.

### D3 — Real, deterministic DSP via scipy (no AI)
Filters use `scipy.signal` (zero-phase Butterworth + IIR notch), stable on short
recordings. Bandpass / highpass / lowpass / notch / reference are all supported. No
learned state, no randomness.

### D4 — Self-contained deterministic ICA (reproducible artifact removal)
Artifact removal implements ICA with a compact, self-contained FastICA using a fixed
(non-random) initialization — bit-for-bit reproducible, no stochastic state, and no
extra dependency (avoids sklearn/picard fragility). Plus adaptive filtering
(least-squares EOG regression), interpolation, channel repair, and noise suppression.
Every method returns a new array and never mutates its input.

### D5 — Raw EEG is immutable; the clean signal is a separate, content-addressed asset
The raw store is read-only here. The cleaned signal is written to a *separate*
`ProcessedSignalStore` (deterministic quantized bytes, checksum + fingerprint +
integrity verify). `SignalIntegrityValidator` asserts raw immutability and full
raw → processed traceability (a contiguous step-fingerprint chain).

### D6 — Artifact-aware default pipeline; average-reference is opt-in
The default clean pipeline always applies a bandpass + powerline notch, and
*conditionally* applies channel repair / ICA / adaptive filtering / noise suppression
when the corresponding artifact is detected. **Average re-referencing is intentionally
not in the default pipeline**: it is montage-dependent and, on low-channel recordings
where channels share content (as the P1 EDF/BDF fixtures do), CAR cancels the shared
signal. It remains a fully implemented, unit-tested filter that callers may opt into.
This keeps the default behaviour information-preserving while satisfying P2-C.

### D7 — Reuse the shared audit + lineage (no parallel systems)
Audit reuses the single hash-chained `ImmutableAuditLog` (`SignalAuditRecord`); lineage
reuses the shared `ml.lineage.LineageTracker`. No new audit or lineage system is
introduced.

### D8 — Reuse the P1 EEG fixtures (no synthetic replacements)
Tests operate on the real P1 fixtures in `tests/fixtures/eeg/` (EDF/EDF+/BDF/BDF+/FIF/
SET). Edge cases (flat/saturated/dropout channels, powerline, EMG, NaNs) are exercised
by injecting artifacts *into arrays loaded from those real fixtures* — not by creating
new synthetic fixture files.

## 3. Consequences

- The deliverable executes with complete traceability: a real EEG file enters, is
  loaded, quality-assessed, artifact-detected, cleaned, stored, tracked, audited, and
  traced — `verify_chain` proves Patient → Case → EEG → Processed.
  `python -m scripts.verify_productization_p2` exercises all 15 phase-completion
  criteria; the signal suite passes and the full repository suite remains green.
- No new runtime dependencies beyond P1's (scipy/mne already pinned in P1). The ICA is
  dependency-free.
- Acyclic DAG preserved; P1 and V0–V4 remain intact (P2 only reads/extends the shared
  lineage/audit and the P1 raw store).

## 4. Scope guard (explicitly NOT built — NR-13)

Feature extraction, model training, inference, predictions, classification, clinical
analytics, FastAPI, database systems, authentication, frontend, deployment,
monitoring, Productization P3+, and Version 5.

## 5. Follow-ups / recorded debt (NR-2)

- Richer, montage-aware re-referencing (with bad-channel exclusion) and clinically
  tuned filter defaults are a natural next increment.
- ICA component classification here is a deterministic ocular-correlation heuristic; a
  future phase may add template/topography-based classification (still no learned
  models in the signal layer).
- Durable, checksummed persistence for the processed-signal store + registry (shared
  with the inherited Gap G3) remains future work behind the same contracts.
