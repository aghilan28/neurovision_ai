# ADR-0024 — DRP-1: Real Dataset Integration Program

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Deployment Remediation Program DRP-1 (post-audit remediation)
> **Builds on:** ADR-0001 … ADR-0023 (Productization P1–P10 + the Independent Production
> Reality Audit)
> **Resolves:** Audit critical blocker — *NO REAL DATASETS INTEGRATED*
> **Enforces / honors:** AP-6/NR-9/NR-10 (determinism), AP-5/AP-8/NR-11 (traceability),
> AP-7/NR-8 (boundaries), NR-6 (reuse), AP-9/NR-5 (this record), NR-13 (scope), NR-2 (honesty)

## 1. Context

The Independent Production Reality Audit found the platform technically sound but
**clinically unusable**, with its #1 critical blocker being that **no real dataset had been
integrated** — only synthetic fixtures, manifests, and connector scaffolding existed. DRP-1
adds the governed external-dataset lifecycle that closes that *integration-framework* gap.
The scope is strictly dataset integration: no model training, no inference/frontend/backend/
operations changes (NR-13).

## 2. Decisions

### D1 — A new governed `backend/dataset_integration` subsystem
Adds inventory, registration, validation, governance metadata, readiness, lineage, audit, and
reports for external EEG corpora. It manages datasets; it trains no models and modifies no
other subsystem. As a `backend` package it obeys the import DAG (imports `ml` + sibling
`backend`, never `frontend`; enforced by `tests/test_boundaries.py`).

### D2 — Manifest-based inventory; never download
The mandatory corpora (TUH EEG, CHB-MIT, Temple/TUSZ, Siena Scalp, Bonn) are inventoried from
local JSON manifests carrying **accurate public metadata** (format, channels, sampling,
counts, license, attribution, source URL). No network access; recordings are never
materialized. Any future corpus is supported by supplying its manifest.

### D3 — Reuse the model-foundation connector framework; don't modify it
TUH/CHB-MIT/Temple registration delegates to the existing `ExternalDatasetConnector` and
cross-references the produced model-foundation `DatasetRecord` id (integration, not
duplication). Siena/Bonn have no connector and are validated locally with the same manifest
contract. The model-foundation `DatasetSource` enum is **not** modified (forbidden change).

### D4 — Reuse shared lineage/audit/validation
One `ml.lineage` tracker (chain **Source → Dataset → Version**), the shared `ImmutableAuditLog`
(bound to `DatasetAuditRecord`), and `ml.validation.ValidationReport`. No parallel systems.

### D5 — Governance is metadata only
License/restrictions/attribution/ownership/source are recorded; the subsystem makes **no
legal interpretation and no compliance claim**. Governance *status* measures documentation
completeness, not legal validity.

### D6 — Readiness = integration-readiness, not clinical readiness
Readiness scores completeness/integrity/validation/governance/registration/traceability into
NOT_READY / PARTIALLY_READY / READY. It explicitly does **not** assert that recordings are
present or that models are clinically valid.

## 3. Consequences

- `python -m scripts.verify_drp1_dataset_integration` → **ALL 15 CRITERIA PASS**; all five
  mandatory corpora reach **READY**, are traceable (Source→Dataset→Version), audited, and (for
  TUH/CHB-MIT/Temple) cross-referenced to model foundation.
- The new suite adds 15 tests; the full repository suite is **851 passed** (was 836). `ruff`
  clean on all new code; `tests/test_boundaries.py` green.
- No new runtime dependencies; the subsystem runs offline and deterministically.

## 4. Scope guard (explicitly NOT built — NR-13)

Model training/tuning, inference/prediction changes, frontend/backend/operations changes,
FastAPI, clinical validation, DRP-2+.

## 5. Honesty statement (NR-2)

DRP-1 closes the **dataset-integration framework** blocker — the governed on-ramp for real
corpora (inventory/registration/validation/governance/readiness/lineage/audit). It does **not**
by itself download data, retrain/tune models, or perform clinical validation; those remain open
conditions from the P10 certification (Gap G1) and from the audit, to be addressed by later
remediation phases. Manifest `location` fields are deploy-time placeholders.
