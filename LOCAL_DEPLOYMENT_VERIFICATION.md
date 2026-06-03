# Local Deployment Verification

## Verification command

Command run in this workspace:

`pytest -q tests/test_server_entrypoint.py`

## Result

The latest run completed with 16 passed tests.

## Verified behaviors

- The real ASGI app imports and serves correctly.
- Health, liveness, and readiness probes are available.
- The real production app exposes the frontend HTML routes (`/`, `/login`, `/dashboard`, `/upload`, `/analysis`, `/prediction`, `/reports`).
- The startup and recovery path remains intact for deployment runtime use.

## Deployment interpretation

This is the fresh evidence set to use for the Render deployment verification package and for confirming the route fix is present in the current mainline state.
