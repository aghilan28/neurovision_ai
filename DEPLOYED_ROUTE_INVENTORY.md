# Deployed Route Inventory

## Current deployed route set

The real production app exposes the following route family:

- HTML UI routes: `/`, `/login`, `/dashboard`, `/upload`, `/analysis`, `/prediction`, `/reports`
- Operational probes: `/health`, `/livez`, `/readyz`
- API surface: `/v1/*` routes from the application-platform backend

## What this means for Render

Render serves the app object directly. The deployed route tree must therefore be the real FastAPI app from `backend.application_platform.server.app`, not an API-only shim or an older frontend gateway path.

## Verification status

Verified in the workspace with the route regression test in `tests/test_server_entrypoint.py`, which checks the UI pages and confirms the real deployment app serves them with HTTP 200.
