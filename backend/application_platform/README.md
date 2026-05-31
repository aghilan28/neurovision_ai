# Real Product Application (`backend/application_platform`) — Track 3

Closes the Production Reality Audit blocker **NO REAL PRODUCT APPLICATION.** It turns the
model platform (P1-P10 + DRP-1..6 + Track 1 + Track 2) into a **usable product**: a real
**FastAPI** HTTP API + governed user workflows.

It serves users through an API — and nothing more. It retrains no models and modifies no
datasets, Track 1, Track 2, persistence, security, or deployment.

## The user workflow

```
register -> login -> upload real EEG (EDF/EDF+/BDF/BDF+)
  -> validate + extract metadata
  -> analyze (validate -> metadata -> features -> select model -> inference -> results)
  -> prediction + confidence + calibration + model info + evidence
  -> report (JSON / HTML / PDF)
  -> application readiness: NOT_READY / PARTIALLY_READY / READY_FOR_USERS
```

## HTTP API (`/v1`)

| Method + path | Purpose |
|---|---|
| `GET /health` | liveness + platform version |
| `GET /v1/dataset/status` | Track-1 dataset status |
| `GET /v1/model/status` | active model + readiness |
| `POST /v1/auth/register` | register a user |
| `POST /v1/auth/login` | obtain a bearer token |
| `POST /v1/uploads` | upload a real EEG (base64) → validate + analyze → prediction |
| `GET /v1/analyses/{id}/prediction` | prediction + confidence + evidence |
| `GET /v1/analyses/{id}/reports?type=&format=` | report set; `format=json\|html\|pdf` |
| `GET /v1/readiness` | application readiness |

Typed Pydantic contracts, versioned, deterministic, documented (auto-generated OpenAPI).
`create_app(service)` builds the app around a hub instance, so a `TestClient` drives the
real HTTP surface in tests + the verification script.

## Reuse (no duplicate logic, no new architecture)

Wraps `backend.application_backend.ApplicationBackendService`, which already orchestrates the
reused P1-P5 upload → validate → process → features → select model → inference → prediction +
confidence + calibration + explanation workflow over a shared `ml.lineage` tracker + the
shared `ImmutableAuditLog`. Track 3 adds the bounded upload step, the prediction-request/
result projection + evidence bundle, JSON/HTML/PDF reports, a product registry, the
application-readiness engine, and the product lineage. The Track-2 architectures and the
Track-1 real recordings are reused as-is.

## Bounded analysis (honest)

Real clinical recordings are hours long (the CHB-MIT files are ~1 h / 921 600 samples) and
the reused P1-P5 pipeline (filtering + ICA + feature extraction) is too slow on a full
recording for an interactive product. The product therefore analyses a deterministic
**leading segment** (default 20 s, `DEFAULT_ANALYSIS_SECONDS`): the full upload is preserved
intact; only the analysis is bounded (a clinical-epoch approach). Cropping reuses the
platform MNE reader + a self-contained canonical EDF writer; it modifies no reused service.

## Lineage (required chain)

```
Dataset -> Recording -> Model -> Prediction Request -> Prediction Result -> Report
```

The prediction-request node parents both the upload node and the model node, so one
`verify_chain` from a report reaches the recording + the model. Audit is the shared
`ImmutableAuditLog`; lineage is the single `ml.lineage` tracker — no parallel systems.

## Run it

```bash
# the 15 final-validation criteria over the real CHB-MIT corpus through the real API
python -m scripts.verify_track3_application       # NV_TRACK1_NO_DOWNLOAD=1 forbids network

# tests (network-free; real EDF fixtures + the real FastAPI TestClient)
python -m pytest tests/test_application_platform.py tests/test_application_platform_e2e.py
```

## Boundary & determinism

Imports `ml` + sibling `backend` (`application_backend`, `dataset_acquisition`,
`real_model_training`, `eeg_foundation`, `model_foundation`) + the external FastAPI stack —
never `frontend` (enforced by `tests/test_boundaries.py`, which governs only the internal
module DAG). Ids/fingerprints are content-addressed; reports are pure functions of
deterministic records, so a workflow renders byte-identical JSON/HTML/PDF across runs.

See [`docs/DESIGN.md`](./docs/DESIGN.md) and [`docs/DECISIONS.md`](./docs/DECISIONS.md), and
the decision record [`ADR-0032`](../../.gcc/decisions/ADR-0032-track3-real-product-application.md).
