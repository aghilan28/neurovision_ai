# Deployment Entrypoint Audit

## Objective

Audit the production deployment entrypoint and confirm that the real application-platform startup path is what Render/uvicorn should execute.

## Authoritative path

The verified production path is:

1. `scripts/serve_neurovision.py` reads config and starts uvicorn with the real FastAPI app.
2. `backend/application_platform/server/factory.py` builds `ApplicationPlatformService` and the real `FastAPI` app.
3. The same app exposes health/readiness and the frontend HTML routes (`/`, `/login`, `/dashboard`, `/upload`, `/analysis`, `/prediction`, `/reports`).

## What changed

- The deployment startup path now goes through the real application-platform server factory instead of the legacy cohort/bootstrap path.
- The app is bound with Render-compatible host/port handling (`0.0.0.0` and `PORT` from the environment).
- The production app exposes the HTML surface that was missing during the route regression.

## Evidence

- `pytest -q tests/test_server_entrypoint.py` → 16 passed.
- The route regression test verifies `GET /`, `/login`, `/dashboard`, `/upload`, `/analysis`, `/prediction`, `/reports` all return HTTP 200 through the real deployment app.

## Deployment conclusion

The deployment entrypoint is now aligned with the real production architecture and is suitable for Render-style execution.
