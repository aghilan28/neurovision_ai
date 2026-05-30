# Application Frontend Platform (`frontend/application_frontend`) — Productization P7

Transforms the application backend into a **usable product**: a real frontend through
which a user can log in, upload an EEG, run an analysis, receive a prediction, view its
confidence + explanation, and access reports. The objective is *user interaction* —
**no deployment, monitoring, or cloud infrastructure** (all out of scope).

```
log in → upload EEG → run analysis → receive prediction →
view confidence → view explanation → access reports
```

## The boundary that shapes everything (NR-8)

`frontend/` may import **no** domain module — not even `backend` as code (enforced by
`tests/test_boundaries.py`). So this subsystem is **stdlib-only** and talks to the
backend exclusively through an abstract **gateway port** (the API contract), exchanging
plain dicts that mirror the backend's *actual* `v1` API (`ApiOperation` vocabulary,
`ApiRequest` params, `ApiResponse` body/status).

```
frontend/application_frontend  ──(BackendGateway port: dict in / dict out)──►  ???
                                                                                │
scripts/application_frontend_gateway.LiveBackendGateway  ───────────────────────┘
    (the ONLY place that imports both layers — drives the real ApplicationAPI)
```

This is the canonical frontend↔backend boundary: **API-only, no code coupling**. The
frontend contains **no business logic** and **bypasses no service** — every action is a
backend API call; it only validates fields for UX, manages deterministic navigation
state, and renders deterministic static HTML.

## Layout (P7-A)

```
application_frontend/
  version.py        # version identities (stdlib only)
  gateway.py        # BackendGateway port + the v1 operation/status contract vocabulary
  util.py           # deterministic stdlib fingerprint + HTML escaping
  domain.py         # FrontendUser/Session/Upload/Workflow/Prediction/Report/… (P7-B)
  actions.py        # ActionResult (controller return type)
  state/            # deterministic ApplicationState (P7-I)
  forms/            # form descriptors + client-side field validation
  auth/             # AuthController — login/register/logout/session handling (P7-C)
  uploads/          # UploadController — upload + history (P7-E)
  workflows/        # AnalysisController — start analysis, reflect backend stages (P7-F)
  predictions/      # PredictionController + prediction view (P7-G)
  reports/          # ReportController + reports view, view/download/history (P7-H)
  components/       # reusable view-model fragments (nav, kv, table, form, stages, …)
  pages/            # page builders (login, register, dashboard, upload, analysis, …)
  layouts/          # deterministic static HTML renderer (inline CSS, no JavaScript)
  validation/       # FrontendValidator — 8 flow/state/UI integrity checks (P7-J)
  reporting.py      # frontend validation/workflow/state/integration reports (P7-L)
  application.py    # FrontendApp — the controller tying state + gateway + pages
  docs/             # DESIGN.md, DECISIONS.md
  tests/            # pointer to the repository-root tests (see tests/README.md)
```

## Quick start (through the seam)

```python
from scripts.application_frontend_gateway import build_live_app   # scripts may import both layers

svc, gateway, app = build_live_app(cohort_files)     # real backend + trained model + FrontendApp
app.register("dr.smith", "secret-pass-1", "secret-pass-1", "clinician")
app.login("dr.smith", "secret-pass-1")
app.dashboard()
upload_id = app.upload("rec.edf", open("rec.edf", "rb").read()).data["upload"]["upload_id"]
analysis  = app.start_analysis(upload_id)
html = app.render_prediction(analysis.data["workflow"]["analysis_id"])   # static HTML page
```

## Determinism & faithful uncertainty

* Pages are **deterministic static HTML** (inline CSS, **no JavaScript**, no external
  assets); the same state always renders byte-identical HTML.
* UI state is deterministic and **secret-free**: the raw session token lives only in
  volatile state and is never serialized or rendered (the snapshot holds at most a token
  *fingerprint* via the backend).
* **Uncertainty is always shown** alongside the label (confidence level + score +
  calibration), never flattened (NR-4).

## Verify

```bash
python -m scripts.verify_productization_p7                  # all 15 phase-completion criteria
python -m scripts.build_application_frontend_snapshot --out app_frontend_snapshot.json
python -m pytest tests/test_application_frontend.py tests/test_application_frontend_e2e.py
```

See `.gcc/decisions/ADR-0020-productization-p7-application-frontend.md`.
