# ADR-0037 — DBE-4: Persistence Wiring & State Durability Fix

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Deployment Blocker Elimination Program — DBE-4
> **Builds on:** ADR-0001 … ADR-0036 (Productization + DRP + Tracks 1-4 + DBE-1/2/3)
> **Resolves:** Final Hostile QA Audit CRITICAL blocker — *APPLICATION STATE DOES NOT SURVIVE RESTART*
> **Enforces / honors:** AP-6/NR-9/NR-10 (determinism), AP-5/AP-8/NR-11 (traceability),
> AP-7/NR-8 (boundaries), NR-6 (reuse, no parallel systems), AP-9/NR-5 (this record),
> NR-13 (scope), NR-2 (honesty)

## 1. Context & root cause (reproduced)

The Final Hostile QA Audit found that the Track-3 product held all application state —
`_uploads`, `_analyses`, `_reports`, the duplicate index, registry, audit, lineage — in
**in-memory dicts** on `ApplicationPlatformService`. A DRP-4 persistence platform existed but
was **never wired into the application lifecycle**, so a restart produced a fresh empty service
and all uploads/predictions/reports were lost. (Reproduced: upload on one instance, construct a
fresh instance, `get_analysis` raises `KeyError`.)

DBE-4 resolves **only** this blocker. Scope is strictly persistence wiring — no changes to
datasets, models, inference, security, deployment/Docker, or token handling, and **no new
database architecture / persistence framework**.

## 2. Decisions

### D1 — Reuse the DRP-4 `StorageEngine` (no parallel persistence; DBE4-C)
A new `application_platform/persistence.py` wires the application to
`backend.persistence_platform.StorageEngine` (the durable, content-addressed, checksum-verified
filesystem-JSON store). Each accepted `AnalysisOutcome` (+ report payloads + duplicate-index
entry + model snapshot) is serialized to durable JSON keyed by its analysis id under
`<root>/app.analyses/<analysis_id>.json`. No new DB, no new framework.

### D2 — Durable on write, recover on startup (DBE4-D)
`ApplicationPlatformService` gains a `persistence_root` (or derives one from `workspace_dir` /
`NV_PERSISTENCE_DIR` → `<workspace>/app_state`). On each accepted analysis the outcome is
persisted; on **construction** the store is replayed: each outcome is reconstructed (new domain
`from_dict` methods), the in-memory views are repopulated, the duplicate index is re-seeded, the
model snapshot is restored, and the registry records are re-registered. Recovery never raises —
a corrupt record is skipped and recorded in the `RecoveryReport.errors`.

### D3 — Audit + lineage references survive (DBE4-E)
Each persisted record already carries its `audit_head` and `lineage_id`, so the
Dataset → Upload → Prediction → Report → Audit → Lineage **references** are intact on the
recovered records, the recovered registry is orphan-free, and the audit chain still verifies.

### D4 — Retrieval workflows from persisted state (DBE4-F)
New service accessors (`get_upload` / `get_prediction` / `get_report` / `get_readiness` /
`list_analyses`) and API endpoints (`GET /v1/uploads/{id}`, `GET /v1/analyses`,
`GET /v1/analyses/{id}`, `GET /v1/persistence`) serve recovered state directly — no
live-workflow reconstruction.

### D5 — Ephemeral remains the default-without-config (backward compatible)
If neither a workspace nor a persistence root is configured, the service stays ephemeral
(historical behaviour) — so existing tests and in-process uses are unchanged. Production (and
the DBE-2 container, which mounts `nv_data` and sets `NV_WORKSPACE_DIR`) is durable.

### D6 — Determinism (NR-9/NR-10)
Ids are content-addressed, so recovery reproduces identical analysis/prediction/report ids;
storage is canonical JSON (deterministic bytes + checksum). Repeated restarts reproduce the
same recovered state.

## 3. Consequences

- `python -m scripts.verify_dbe4_persistence` → **ALL 15 CRITERIA PASS**: the root cause is
  reproduced; with persistence wired, upload → predict → report then a real **restart** (fresh
  service at the same root) recovers the upload/prediction/report/analysis/readiness, retrieval
  endpoints serve recovered state, and registry/audit/lineage references are intact.
- New suite `tests/test_persistence_durability.py` (13 tests) incl. restart, repeated restart,
  API retrieval, report export after restart, and the ephemeral-vs-durable contrast.
- New domain `from_dict` reconstructors added (round-trip with the existing `to_dict`).
- `ruff` clean; `tests/test_boundaries.py` green; full suite remains green; no new dependencies.

## 4. Scope guard (explicitly NOT done — NR-13)

Did not fix invalid-token 500; did not modify Docker/deployment assets, datasets, models,
inference, security, or Track 1-4; created no new database/persistence framework. The
remaining audit finding (invalid-token → 500) is out of scope here.

## 5. Honesty statement (NR-2)

DBE-4 makes application state **durable across restarts** — verified by persisting on one
instance, constructing a brand-new instance at the same root (a real cold restart), and
retrieving the upload/prediction/report/analysis/readiness from recovered state with integrity
intact. It reuses the existing DRP-4 storage engine (filesystem JSON) — durable and
restart-recoverable, but not a distributed/cloud database (that remains a deployment concern,
out of scope). The only remaining open audit finding is invalid-token → 500 (its own phase).
