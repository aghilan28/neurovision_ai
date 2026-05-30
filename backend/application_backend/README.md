# Application Backend Platform (`backend/application_backend`) — Productization P6

Exposes the platform's P1–P5 capabilities through governed **application backend
services**, transforming the internal platform into an application backend. The single
use case it delivers, end to end, is:

```
authenticate → upload EEG → start analysis →
prediction + confidence + explanation → retrieve results
```

…through in-process application backend services. **No frontend, deployment,
monitoring, or cloud infrastructure** (all out of scope for this phase).

## What it does (and does not)

* **Does:** local authentication, user management, an EEG application workflow that
  *orchestrates* the existing P1–P5 services, a versioned (`v1`) in-process API,
  request + integrity validation, application storage, a single registry, shared audit
  + lineage, deterministic reports.
* **Does not:** train parallel models, re-implement EEG/signal/feature/inference logic,
  open network sockets, serve HTTP, deploy, monitor, or touch cloud infrastructure. It
  **reuses** P1–P5 and **duplicates no business logic**.

## Built strictly on P1–P5 (no parallel systems)

The hub wires the reused services over **one** shared `ml.lineage.LineageTracker` and
the shared tamper-evident `ImmutableAuditLog`:

| Stage | Reused service (unchanged) |
|-------|----------------------------|
| Case  | `backend.clinical_cases.CaseService` |
| Validate / ingest EEG | `backend.eeg_foundation.EEGFoundationService` (P1) |
| Process | `backend.signal_processing.SignalProcessingService` (P2) |
| Features | `backend.feature_engineering.FeatureEngineeringService` (P3) |
| Model | `backend.model_foundation.ModelFoundationService` (P4) |
| Predict / confidence / calibration / explanation | `backend.inference_foundation.InferenceFoundationService` (P5) |

## Traceability — the required chain

A workflow records a **join** lineage node parenting both the *upload* node and the
*prediction* node, so a single `verify_chain` proves:

```
User → Upload → EEG → Processed → Feature → Model → Prediction
```

The P1–P5 chain (`… → EEG → Case → Patient`) is preserved intact and only referenced —
never modified. There is **no parallel audit or lineage system**.

## Layout (mirrors the established subsystem shape)

```
application_backend/
  version.py            # version identities + deterministic epoch + secure-default params
  models/               # domain records + closed vocabularies (P6-B)
  identity/             # deterministic {kind}+{hash16} ids (user/session/upload/…)
  auth/                 # passwords (PBKDF2), tokens, AuthService (P6-C)
  users/                # UserService (P6-D)
  workflows/            # EegWorkflowService — orchestration only (P6-E)
  api/                  # versioned request/response contracts + ApplicationAPI (P6-F)
  validation/           # RequestValidator (P6-G) + ApplicationIntegrityValidator (P6-K)
  storage/              # in-memory stores + content-addressed upload byte store (P6-H)
  registry/             # BackendRegistry — no orphan records (P6-I)
  audit/                # shared ImmutableAuditLog bound to BackendAuditRecord (P6-J)
  lineage/              # user/session/upload/workflow nodes on the shared tracker (P6-J)
  reports/              # deterministic report builders (P6-L)
  schemas/              # an entity contract per object (P6-M)
  service.py            # ApplicationBackendService — the composition hub
  docs/                 # DESIGN.md, DECISIONS.md
  tests/                # pointer to the repository-root tests (see tests/README.md)
```

## Quick start

```python
from backend.model_foundation import ModelArchitecture
from backend.application_backend import (
    ApplicationBackendService, ApiRequest, ApiOperation,
)

svc = ApplicationBackendService()                      # secure defaults
svc.prepare_model([("P-0", "C-0", "rec0.edf"),
                   ("P-1", "C-1", "rec1.edf"), ...],   # patient-disjoint cohort
                  architecture=ModelArchitecture.EEGNET, dataset_key="cohort", seed=7)
api = svc.api

api.handle(ApiRequest(ApiOperation.REGISTER_USER,
                      {"username": "dr.smith", "password": "secret-pass-1", "roles": ["clinician"]}))
token = api.handle(ApiRequest(ApiOperation.LOGIN,
                              {"username": "dr.smith", "password": "secret-pass-1"})).body["token"]
up = api.handle(ApiRequest(ApiOperation.UPLOAD_EEG,
                           {"filename": "rec.edf", "content": open("rec.edf", "rb").read()}, token=token))
an = api.handle(ApiRequest(ApiOperation.START_ANALYSIS,
                           {"upload_id": up.body["upload_id"]}, token=token))
pred = api.handle(ApiRequest(ApiOperation.RETRIEVE_PREDICTION,
                             {"analysis_id": an.body["analysis_id"]}, token=token))
```

## Determinism & security

* All ids, versions, fingerprints, and report contents are **content-derived** (no
  wall-clock, no randomness) — re-running reproduces the same `prediction_id` and
  workflow version.
* The **only** non-deterministic inputs are authentication secrets (password salts +
  session tokens), drawn from a secure entropy source by default and from an injectable
  deterministic source in tests. Secrets never enter a content hash; `UserRecord`
  carries no password/salt, and `SessionRecord` stores only a token *fingerprint*.

## Verify

```bash
python -m scripts.verify_productization_p6          # all 15 phase-completion criteria
python -m pytest tests/test_application_backend.py tests/test_application_backend_e2e.py
```

## Boundary (NR-8)

Part of the `backend` Application layer. Imports `ml` + sibling `backend` subsystems
only; **never** imports `frontend`. Authentication is **local-only** (no social login,
no OAuth providers).

See `.gcc/decisions/ADR-0019-productization-p6-application-backend.md`.
