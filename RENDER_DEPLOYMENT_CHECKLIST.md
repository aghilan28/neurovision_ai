# Render Deployment Checklist

## Pre-deploy

- [ ] Confirm the deployment command uses the real application-platform startup path.
- [ ] Confirm the service binds to `0.0.0.0` and respects `PORT`.
- [ ] Confirm the runtime app is `backend.application_platform.server.app:app` (or the equivalent production entrypoint).

## Post-deploy validation

- [ ] Open `/health` and confirm HTTP 200.
- [ ] Open `/livez` and confirm HTTP 200.
- [ ] Open `/readyz` and confirm readiness is reported honestly.
- [ ] Open `/`, `/login`, `/dashboard`, `/upload`, `/analysis`, `/prediction`, `/reports` and confirm they return HTTP 200.

## Regression protection

- [ ] Keep `tests/test_server_entrypoint.py` in the verification suite for startup, health, and frontend-route exposure.
- [ ] Re-run the route regression tests after any deployment-path changes.

## Rollback trigger

If the browser-facing pages return 404 after deployment, treat the route wiring on the production app object as the first fault domain to inspect.
