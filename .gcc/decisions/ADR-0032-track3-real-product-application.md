# ADR-0032 — Track 3: Real Product Application Program

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** Product Completion Program — Track 3 (Real Product Application)
> **Builds on:** ADR-0001 … ADR-0031 (Productization P1–P10 + DRP-1…DRP-6 + Track 1 + Track 2)
> **Resolves:** Production Reality Audit blocker — *NO REAL PRODUCT APPLICATION*
> (no user-facing product, API layer, or upload/prediction/report workflow)
> **Enforces / honors:** AP-6/NR-9/NR-10 (determinism), AP-5/AP-8/NR-11 (traceability),
> AP-7/NR-8 (boundaries), NR-6 (reuse, no parallel systems), AP-9/NR-5 (this record),
> NR-13 (scope), NR-2 (honesty)

## 1. Context

Tracks 1 + 2 delivered **real datasets** and **real trained models** (READY_FOR_SERVING).
The audit's next blocker is *no real product application*: there was no user-facing product,
no HTTP API, and no upload / prediction / report workflow. (The P6 application backend +
P7 frontend were in-process / presentation-only by design — there was no real HTTP transport.)

Track 3 closes that blocker by turning the model platform into a **usable product**: a real
**FastAPI** HTTP API + governed user workflows (upload a real EEG → validate → features →
select model → inference → prediction + confidence + evidence → report → readiness). Scope
is strictly the product application layer — no retraining, no dataset changes, no Track 1/2
changes, no persistence / security / deployment changes (NR-13).

## 2. Decisions

### D1 — A new governed `backend/application_platform` subsystem
It mirrors the platform subsystem shape (models, identity, api, uploads, workflows,
predictions, reports, validation, readiness, registry, audit, lineage, schemas, service). As
a `backend` package it obeys the import DAG (imports `ml` + sibling `backend`, never
`frontend`; enforced by `tests/test_boundaries.py`).

### D2 — A real FastAPI HTTP API (T3-C) — the directive overrides the prior "no HTTP" stance
The directive explicitly requires FastAPI. FastAPI/Starlette/Pydantic are **external**
packages, so importing them under `backend/` does not violate the internal-import boundary
test (which only governs the internal module DAG). The API (`api/`) is a thin, typed,
versioned (`/v1`) dispatcher with **no business logic**; it delegates to the
`ApplicationPlatformService` hub. `create_app(service)` builds the app around a hub instance
so a `TestClient` drives the real HTTP surface deterministically.

### D3 — Reuse `application_backend` (no duplicate workflow logic; NR-6)
`application_backend.ApplicationBackendService` already orchestrates the reused P1-P5
upload → validate → process → features → select model → inference → prediction + confidence +
calibration + explanation workflow over a shared `ml.lineage` tracker + the shared
`ImmutableAuditLog`. Track 3 wraps it (register / login / upload / start_analysis / facets /
reports via its in-process API) and adds the product layer (bounded upload, prediction
projection + evidence bundle, JSON/HTML/PDF reports, product registry / readiness / lineage).
The five Track-2 architectures and the real recordings are reused as-is.

### D4 — Bounded analysis segment (T3-D) — a clinical-epoch product choice
Real recordings are hours long (CHB-MIT files are ~1 h / 921 600 samples) and the reused
P1-P5 pipeline (filtering + ICA + features) is far too slow on a full recording for an
interactive product. The product therefore analyses a deterministic **leading segment**
(default 20 s): the full upload is preserved intact; only the analysis is bounded. Cropping
reuses the platform's MNE reader + a self-contained canonical EDF writer (the `tests` writer
is import-forbidden from `backend`); it modifies no reused service.

### D5 — JSON / HTML / PDF reports (T3-G), all deterministic + stdlib
Report builders are pure functions of the deterministic records. Exporters are stdlib-only:
canonical JSON, escaped static HTML, and a minimal valid PDF writer (no `reportlab`/
`weasyprint` dependency). A given workflow renders byte-identical reports across runs.

### D6 — `READY_FOR_USERS` readiness (T3-I) + shared audit/lineage (T3-J)
A new classification: **NOT_READY < PARTIALLY_READY < READY_FOR_USERS**, scored over seven
dimensions (upload / prediction / workflow / report / registry / audit / lineage). All nodes
are recorded in the single `ml.lineage` tracker; events on the shared `ImmutableAuditLog`.
The prediction-request node parents both the **upload** node and the **model** node,
realizing **Dataset → Recording → Model → Prediction Request → Prediction Result → Report**;
one `verify_chain` from a report reaches the recording + the model (and, through the reused
`application_backend` workflow lineage, the patient).

### D7 — A real pre-existing P2 bug fixed (in scope)
The real-EEG product workflow surfaced a genuine bug in `signal_processing` (P2):
`detect_movement` called `float(np.clip(x, 0, 1) + 0.5, 0.0, 1.0)` — `float()` with 3 args —
which only triggers on real long recordings (the tiny committed fixtures never hit the
movement-detection path). It blocked the entire real-data workflow. `signal_processing` is
**not** in Track 3's forbidden-modification list, so the one-line typo was fixed
(`float(np.clip(x + 0.5, 0.0, 1.0))`). All prior P2 tests remain green.

## 3. Consequences

- `python -m scripts.verify_track3_application` → **ALL 15 CRITERIA PASS** against the real,
  locally-acquired CHB-MIT corpus through the **real FastAPI HTTP API**: register → login →
  upload a genuine 23-channel/256 Hz EDF → prediction (label + high confidence + evidence) →
  JSON/HTML/PDF reports → **READY_FOR_USERS**, fully traceable + audited, deterministic.
- New suite adds **20 tests** (real `TestClient` HTTP + real EDF fixtures); full repository
  suite **1009 passed** (was 989). A real-corpus e2e test runs over the genuine PhysioNet
  recordings when available.
- `ruff` clean on all new code; `tests/test_boundaries.py` green; prior verify scripts
  (Track 1, Track 2, DRP-1…DRP-6, productization) unaffected.
- New deps pinned in `requirements.txt`: `fastapi==0.121.2`, `uvicorn==0.34.3`,
  `httpx==0.28.1` — used only by the Track-3 API + tests; never enter a reproducibility hash.

## 4. Scope guard (explicitly NOT built — NR-13)

Model retraining, dataset changes, Track 1/2 changes, persistence-architecture changes,
security-architecture changes, deployment-infrastructure changes. Track 3 builds the product
application layer — **only**.

## 5. Honesty statement (NR-2)

Track 3 delivers a **real, usable product**: a real HTTP API through which a real EEG file is
uploaded, validated, analysed, and predicted on by a real trained model, with a real report
and complete traceability. The product analyses a **bounded leading segment** of each
recording (a deliberate, disclosed clinical-epoch choice for interactivity) — the full upload
is preserved. The prediction reflects the platform's **untuned reference model on real data**
(Tracks 1/2 honesty) — it is evidence of a working end-to-end product, **not** a clinical-
performance claim or clinical decision support. `READY_FOR_USERS` certifies a *complete,
reproducible, traceable user workflow with objective evidence*, not clinical fitness. The API
runs in-process via `TestClient` for verification; production hosting/TLS/scaling remain
deployment concerns (out of scope). This closes the *no real product application* blocker:
NeuroVision can now accept EEG files, validate them, generate predictions, generate reports,
serve users through APIs, track lineage, and score user readiness on **real** recordings and
**real** trained models.
