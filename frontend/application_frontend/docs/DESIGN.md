# Application Frontend Platform — Design (Productization P7)

## Objective

Turn the application backend (P6) into a usable product: a real frontend through which a
user logs in, uploads an EEG, runs an analysis, and receives + reviews a prediction
(confidence, explanation) and its reports. No deployment, monitoring, or cloud.

## The hard boundary (NR-8) and how we honour it

`tests/test_boundaries.py` enforces `ALLOWED["frontend"] = set()` — the frontend imports
**no** domain module, not even `backend`. Every prior NeuroVision frontend is therefore
presentation-only Python. P7 follows the same rule while still being *interactive*:

* The frontend defines an abstract **`BackendGateway`** port — a single
  `handle(operation, params, token) -> dict` that exchanges plain dicts matching the
  backend's real `v1` API (`ApiOperation` values, `ApiRequest` params, `ApiResponse`
  body/status). The frontend speaks the protocol; it imports nothing.
* A concrete **`LiveBackendGateway`** adapter lives at the `scripts/` seam (scripts may
  import any layer) and drives the real `ApplicationAPI`. Tests, the verification script,
  and the snapshot builder wire the real backend through this adapter — so the frontend
  is exercised against **actual contracts, never fakes**.

## Components

* **`FrontendApp`** (controller) — owns deterministic `ApplicationState`, the gateway,
  and the per-concern controllers (`AuthController`, `UploadController`,
  `AnalysisController`, `PredictionController`, `ReportController`). Each action calls the
  gateway and shapes an `ActionResult`; the app updates state and renders.
* **State** — caches the *responses the user has seen* (projected into frontend domain
  objects) + navigation/flash context. Deterministic; the raw token is volatile and never
  serialized.
* **Pages / components / layouts** — page builders produce view-model dicts; the layout
  renderer turns them into deterministic static HTML (inline CSS, no JavaScript). All
  values HTML-escaped.
* **Validation** — `FrontendValidator` runs eight flow/state/UI integrity checks.
* **Reporting** — frontend validation / workflow / state / integration meta-reports.

## Flows

* **Auth (P7-C):** register/login/logout/session handling by consuming the backend auth
  API — no local auth logic. An `unauthorized` response to a *protected* action triggers
  central session-expiration handling (clear state, route to login). A failed *login* is
  bad credentials, not expiration.
* **Upload (P7-E):** forwards file bytes to the backend EEG workflow; supports whatever
  formats the backend accepts; surfaces backend status/findings + an upload history.
* **Analysis (P7-F):** asks the backend to run the orchestration and reflects its stages
  (`upload → validate → process → features → predict → confidence → explanation`) — it
  does not recreate the workflow engine. The analysis summary omits stages, so they are
  enriched from the workflow report for the progress view.
* **Prediction (P7-G):** displays the real prediction asset — label, class probabilities,
  confidence, calibration, explanation summary, model info — uncertainty always shown.
* **Reports (P7-H):** lists/views/downloads the actual backend reports; a validation +
  audit summary is surfaced from fields the backend embeds in those reports.

## Determinism

No wall-clock, no randomness in any rendered output. Two independent runs of the same
journey render byte-identical prediction/report pages and produce the same state
signature. The only non-deterministic backend input (auth secrets) never reaches the
frontend.

## Out of scope (forbidden in P7)

Docker, Kubernetes, cloud deployment, monitoring, observability, CI/CD, Productization
P8+, Version 5. No business logic in the frontend; no bypassing backend services.
