# Real Product Application — Design (Track 3)

## Objective

Turn the model platform into a **usable product**: a real FastAPI HTTP API + governed user
workflows (upload a real EEG → validate → features → select model → inference → prediction →
report → readiness) over real recordings and real trained models — proving a complete user
workflow end-to-end with READY_FOR_USERS.

## Module map

| Module | Phase | Responsibility |
|---|---|---|
| `version.py` | — | version coordinates + `DEFAULT_ANALYSIS_SECONDS` + `DETERMINISTIC_EPOCH` |
| `models/domain.py` | T3-B | closed vocabularies + records (request/upload/prediction/analysis/report/workflow/readiness/registry/audit) |
| `identity/` | — | content-addressed `{kind}+{hash16}` ids |
| `api/` | T3-C | the real **FastAPI** app: typed/versioned `/v1` endpoints; `create_app(service)` |
| `uploads/` | T3-D | validate real EEG bytes (reused reader) + bounded-segment cropping (MNE + canonical EDF writer) |
| `workflows/` | T3-E | drives the reused `application_backend` API (upload → analysis → facets → reports) |
| `predictions/` | T3-F | prediction-request/result projection + the evidence bundle (confidence/calibration/explanation/model) |
| `reports/` | T3-G | 8 report builders + JSON/HTML/PDF exporters (stdlib, deterministic) |
| `readiness/` | T3-I | application-readiness engine (NOT_READY / PARTIALLY_READY / READY_FOR_USERS) |
| `validation/` | — | application integrity validation (the `ok` gate) |
| `registry/` | T3-H | product registry — no orphan records |
| `audit/` | T3-J | the shared `ImmutableAuditLog` (no parallel system) |
| `lineage/` | T3-J | shared `ml.lineage`; Dataset → Recording → Model → Prediction Request → Result → Report |
| `schemas/` | — | a documented contract per entity |
| `service.py` | — | `ApplicationPlatformService` — `prepare_model` / `register` / `login` / `upload_and_analyze` / `reports_for` / `export_report` |

## Request flow

`POST /v1/uploads` → `ApplicationPlatformService.upload_and_analyze`:
1. **T3-D** validate the real EEG bytes (reused `eeg_foundation` reader) + record the upload;
2. crop a deterministic **bounded leading segment** (default 20 s) — the analysis input;
3. **T3-E** drive the reused `application_backend` API over the bounded segment (upload →
   start_analysis → prediction/confidence/explanation facets → reports);
4. **T3-F** project the prediction request + result + the evidence bundle (traceable);
5. **T3-G** build the report set + export JSON/HTML/PDF; mint the report lineage node;
6. register every product entity (no orphans), append audit events;
7. **T3-I** validate integrity + score application readiness; **T3-J** verify the lineage chain.

## Reuse (no parallel systems, no new architecture)

The full upload → prediction workflow is the reused `application_backend` hub (which itself
reuses the P1-P5 pipeline + the model foundation). Track 3 adds only the product layer + the
HTTP transport. The five Track-2 architectures and the Track-1 real recordings are reused.

## Determinism

Content-addressed ids; report builders/exporters are pure functions of deterministic records;
the bounded-segment crop is deterministic. A given workflow renders byte-identical JSON/HTML/
PDF and reproduces the same upload/analysis/prediction ids across independent instances.

## Test strategy

* **Network-free** tests drive the **real** FastAPI surface via `TestClient` over the
  committed real EDF fixtures (a tiny real cohort + a small analysis window), covering the API,
  upload, analysis, prediction, reports (JSON/HTML/PDF), readiness, audit, lineage, registry,
  determinism, and the corrupted-EEG / invalid-request / missing-model conditions.
* A **real-corpus** e2e test runs the full workflow over the locally-acquired PhysioNet
  recordings (23 channels @ 256 Hz) when available.
