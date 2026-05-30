# ADR-0016 — Productization P3: Feature Engineering Platform

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Productization P3
> **Builds on:** ADR-0001 … ADR-0015 (esp. ADR-0014 P1 EEG Foundation, ADR-0015 P2 Signal Processing)
> **Enforces / honors:** AP-1 (vertical population, no re-layering), AP-3/AP-6/NR-9/NR-10
> (determinism/reproducibility), AP-5/AP-8/NR-11 (traceability/audit), AP-7/NR-8
> (boundaries), AP-9/NR-5 (this record), NR-6 (reuse, don't re-implement), NR-13 (scope)
> **Decision owner:** Application/platform engineering (Kiro-assisted, subject to NR-7)

Captures why the Productization P3 **Feature Engineering Platform**
(`backend/feature_engineering`) is shaped as it is, so the rationale survives turnover
(NR-14).

---

## 1. Context

P1 (ADR-0014) made the platform accept a real EEG file; P2 (ADR-0015) turned a raw
asset into a validated clean asset. P3 takes the next narrow step: turn a **processed
EEG asset** into a **validated immutable feature asset** — frequency, temporal,
connectivity, spectral, and topographic features — and nothing else. No model
training, model registry, inference, predictions, classification, or clinical
decisions.

This is **productization**, not a new version or architecture/governance expansion.
It must build strictly on P1 + P2 and reuse existing platform patterns.

## 2. Decisions

### D1 — One new `backend` subsystem, vertical population only (AP-1)
`backend/feature_engineering` mirrors the established subsystem shape (models /
identity / frequency / temporal / connectivity / spectral / topography / registry /
validation / lineage / audit / reports / schemas / service). It imports `ml`, reads
the P2 store, and reuses the shared audit primitive from `backend.clinical_cases.audit`
(intra-`backend` reuse); it never imports `frontend` (enforced by `tests/test_boundaries.py`).

### D2 — Build on P1 + P2; never redesign or duplicate
The layer **reads** the immutable processed-signal bytes from the P2
`ProcessedSignalStore` and references the P2 `ProcessedEEGRecord`. It does not modify,
replace, or re-implement P1/P2. The feature identity is parented on the processed
`signal` id, and its lineage parents the processed-EEG lineage node, so the chain is
**Patient → Case → EEG → Processed → Feature**.

### D3 — Five deterministic, dependency-light engines (no AI)
Features are computed with pure NumPy/SciPy (Welch PSD, Hilbert, coherence,
spectrogram, statistics) — deterministic, no randomness, no learned state. Frequency
(band powers/ratios/relative power/spectral entropy), temporal (statistical/Hjorth/
entropy, per-channel + per-recording), connectivity (coherence/PLV/cross-correlation/
synchronization), spectral representations (PSD/spectrogram/band-summary/histogram),
and topography (channel-layout/regional/spatial-summary/topographic-stat — **structured
only, never images**).

### D4 — Closed vocabularies + structured feature vectors
`FeatureFamily`, `FeatureGroup`, `FeatureScope`, `FrequencyBand` are closed enums.
Every output is a `FeatureVector` carrying family/group/scope/labels/values plus
`shape`+`axes` so matrices (connectivity, spectrogram) stay structured and
content-addressed. No free-form states; no undocumented objects (schemas/contracts).

### D5 — The feature asset is immutable
`FeatureRecord` is a **frozen** dataclass with content fingerprints. It is built once
(version + lineage + audit head computed before construction) and never mutated. The
registry rejects silent overwrite of a version with different content.

### D6 — Determinism is validated, not assumed
The service extracts features **twice** and asserts identical vector fingerprints (the
`feature_determinism` content check). Content validation also covers completeness,
integrity (finite values + shape match), and consistency (per-channel/pair dimensions).

### D7 — Reuse the shared audit + lineage (no parallel systems)
Audit reuses the single hash-chained `ImmutableAuditLog` (`FeatureAuditRecord`);
lineage reuses the shared `ml.lineage.LineageTracker`. The full eight P3-K checks are
produced by `FeatureIntegrityValidator` (content ×4 + registry/audit/lineage/version)
reusing `ml.validation.ValidationReport`.

### D8 — Reuse the P1/P2 assets + fixtures (no replacement systems)
Tests run the real P1 ingest → P2 process → P3 features pipeline over the committed P1
EEG fixtures (EDF/EDF+/BDF/BDF+/FIF/SET). Edge cases use arrays derived from those real
assets — no replacement systems or synthetic feature fixtures.

## 3. Consequences

- The deliverable executes with complete traceability: a real EEG file is loaded,
  validated, cleaned, has features generated into an immutable feature asset, and is
  tracked/audited/traced — `verify_chain` proves Patient → Case → EEG → Processed →
  Feature. `python -m scripts.verify_productization_p3` exercises all 15 criteria; the
  feature suite passes and the full repository suite remains green.
- No new runtime dependencies beyond P1/P2's (numpy/scipy/mne already pinned).
- Acyclic DAG preserved; P1/P2 and V0–V4 remain intact (P3 only reads the P2 store and
  extends the shared lineage/audit).

## 4. Scope guard (explicitly NOT built — NR-13)

Model training, model registry, inference, predictions, classification, clinical
analytics, FastAPI, database systems, authentication, frontend, deployment,
monitoring, Productization P4+, and Version 5.

## 5. Follow-ups / recorded debt (NR-2)

- Durable, checksummed persistence for large feature representations (PSD/spectrogram)
  shares the inherited Gap G3 and is future work behind the same contracts.
- Richer connectivity (band-resolved coherence/PLV) and montage-aware topographic
  coordinates are natural next increments (still no learned models in this layer).
