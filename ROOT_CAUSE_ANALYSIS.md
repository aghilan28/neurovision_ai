# Root Cause Analysis

## Failure mode

The deployed frontend returned `Not Found` because the exposed app surface did not contain the real HTML UI route tree. The startup path was present, but the router wiring on the authoritative production app was incomplete for the browser-facing pages.

## Root cause

The deployment runtime was effectively exposing the API-oriented app surface instead of the full application-platform UI surface. As a result, direct browser navigation to the product pages returned 404 even though the server itself was up.

## Fix applied

The real application-platform server factory now restores the frontend HTML page routes on the production app object that `uvicorn` serves. The change is in `backend/application_platform/server/factory.py`, and regression coverage was added in `tests/test_server_entrypoint.py`.

## Why this resolves the issue

The route tree is now aligned with what the deployment runtime actually serves. Browser navigation, Render health checks, and UI page probes all target the same authoritative app object.
