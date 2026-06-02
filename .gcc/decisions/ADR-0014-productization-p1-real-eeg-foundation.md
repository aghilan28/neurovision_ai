# ADR-0014 — Productization P1: Real EEG Foundation Layer

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Productization P1
> **Builds on:** ADR-0001 … ADR-0013
> **Enforces / honors:** AP-1 (vertical population, no re-layering), AP-3/AP-6/NR-9/NR-10
> (determinism/reproducibility), AP-5/AP-8/NR-11 (traceability/audit), AP-7/NR-8
> (boundaries), AP-9/NR-5 (this record), NR-6 (reuse, don't re-implement), NR-13 (scope)
> **Decision owner:** Application/platform engineering (Kiro-assisted, subject to NR-7)

Captures why the Productization P1 **Real EEG Foundation Layer**
(`backend/eeg_foundation`) is shaped as it is, so the rationale survives turnover
(NR-14).

---

## 1. Context

Through V0–V4 the platform was certified on **synthetic** EEG only — the inherited
Gap **G1** ("synthetic-only data") across every certification package. Productization
P1 closes the first step of G1: the platform must accept a **real EEG file**,
understand it, validate it, and store it as a traceable asset. The scope is
deliberately and narrowly bounded — *no* signal processing, feature extraction,
modelling, inference, analytics, APIs, dashboards, authentication, or deployment.

This is **productization**, not a new version and not architecture/governance
expansion. It must reuse existing platform patterns rather than invent new ones.

## 2. Decisions

### D1 — One new `backend` subsystem, vertical population only (AP-1)
`backend/eeg_foundation` populates the Application layer mirroring the shape of the
existing subsystems (models / identity / ingestion / validation / metadata /
storage / registry / audit / lineage / reports / schemas / service). No layer is
added or re-drawn. It imports `ml` (provenance/lineage/validation) + the shared
audit primitive from `backend.clinical_cases.audit` (intra-`backend` reuse) and
never imports `frontend` (enforced by `tests/test_boundaries.py`).

### D2 — MNE-Python is the real reader; a closed format vocabulary (NR-13)
Real files are read with **MNE-Python** (`mne==1.12.1`; `scipy` for the EEGLAB
`.set` container) — the industry-standard reader — with **no mock/synthetic/fake
parsers** in the ingestion path. The supported set is a **closed vocabulary**:
`EDF, EDF+, BDF, BDF+, FIF, SET`. The precise format is detected from the file's
**bytes** (magic + reserved fields), not its extension, so EDF vs EDF+ and BDF vs
BDF+ are disambiguated and extension/content mismatches are surfaced.

### D3 — Content-addressed identity, never filename-derived
An EEG asset id is `eeg+{hash16}` derived from `(case_id, eeg_key)` where `eeg_key`
is the file's content fingerprint. The same bytes under the same case always yield
the same `asset_id` (idempotent ingestion); a renamed/moved file is the same asset.
The `eeg` kind is parented on `case`, extending the existing identity scheme.

### D4 — Validation returns structured findings, never exceptions
`EEGFileValidator` produces an `EEGValidationResult` (typed `EEGValidationFinding`s
with INFO/WARNING/ERROR/CRITICAL severities) for all mandated conditions: corrupted,
unreadable, unsupported, missing channels, invalid sampling rate, invalid duration,
metadata errors, annotation errors. Ingestion itself never raises. A separate
`EEGIntegrityValidator` checks a *built* asset (identity/registry/storage/metadata/
audit/lineage/version) reusing `ml.validation.ValidationReport` (NR-6).

### D5 — Deterministic metadata, stored independently of raw bytes
`EEGMetadata` is a pure function of the parsed file (same file → same metadata and
signature), carries no raw signal, and is stored independently. The `recording_id`
is content-addressed, not filename-derived.

### D6 — Local, content-addressed storage; no infrastructure
`LocalEEGStore` references raw bytes at `<root>/<fingerprint>/<name>` with a full
sha256 checksum, fingerprint, size, and a `verify()` integrity re-check. **No cloud,
S3, database, or deployment** — only correct architecture behind the
`EEGStorageRecord` contract, swappable by a future durable backend (the inherited
Gap G3).

### D7 — Reuse the shared audit + lineage (no parallel systems); Patient → Case → EEG
Audit reuses the platform's single hash-chained `ImmutableAuditLog` bound to
`EEGAuditRecord`; lineage reuses the shared `ml.lineage.LineageTracker` with the EEG
node parented on the **case** node. A single `verify_chain(asset.lineage_id)` proves
`Patient → Case → EEG Asset`. The EEG subsystem stays decoupled from
`clinical_cases` beyond the audit primitive: the caller wires a Case (created with
the same shared tracker) and passes `case_id`/`patient_id`/`case_lineage_id`.

### D8 — Asset status: REGISTERED / QUARANTINED; reject the truly unusable
A valid file becomes a `REGISTERED` asset; a recognized-but-undecodable (corrupted)
file becomes a `QUARANTINED` asset (still identified, stored, audited, traced, with
a CRITICAL finding). Unreadable/unsupported inputs are rejected before an asset
exists, but always return their structured findings — nothing fails silently. No
broader workflow/lifecycle is built (that would be future work).

## 3. Consequences

- The deliverable executes with complete traceability: a real EEG file enters and
  becomes a registered NeuroVision EEG asset whose lineage verifies
  `Patient → Case → EEG`. `python -m scripts.verify_productization_p1` exercises all
  15 phase-completion criteria; the EEG suite (`tests/test_eeg_foundation*.py`)
  passes and the full repository suite remains green.
- New runtime dependencies (`mne`, `scipy`) are pinned in `requirements.txt` /
  `pyproject.toml`. They are used only by `backend/eeg_foundation` and never enter a
  reproducibility hash. `ruff` is now declared (dev) so the platform's lint/cert
  gate is reproducible from a clean checkout.
- A scoped `filterwarnings` allowance lets third-party (mne/scipy) DeprecationWarnings
  pass while keeping the strict gate for our own code.
- Acyclic DAG preserved; V0–V4 remain intact (EEG only reads/extends the shared
  lineage/audit).

## 4. Scope guard (explicitly NOT built — NR-13)

Signal filtering, artifact removal, feature extraction, model training, inference,
predictions, clinical analytics, FastAPI, PostgreSQL, Redis, authentication,
frontend, Docker/Kubernetes, deployment, monitoring, Version 5, and any later
productization phase.

## 5. Follow-ups / recorded debt (NR-2)

- Durable, checksummed persistence for the EEG store + registry (inherited Gap G3)
  is the natural next increment, behind the same `EEGStorageRecord`/registry
  contracts.
- Real recordings carry PHI in source headers; this layer surfaces only a
  de-identified subject id and records *which* metadata fields were present (keys,
  not values). A future de-identification/consent phase can formalize this.
- Per-channel heterogeneous sampling rates (rare in EDF) are reported via MNE's
  uniform `sfreq`; a future phase can preserve per-signal rates if required.
