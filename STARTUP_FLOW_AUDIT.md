# NeuroVision Deployment Startup Flow Audit

## Summary

The deployment startup path now uses the real application-platform server factory instead of the legacy cohort bootstrap. This removes the direct `prepare_model()` dependency that forced a patient-disjoint cohort with at least two recordings.

## Previous failure mode

The old deployment script wired `scripts/application_frontend_gateway.py` directly into `scripts/serve_neurovision.py`. That legacy adapter calls the backend preparation path that requires real cohort data, which is why startup failed with:

> `ApplicationBackendError: a patient-disjoint cohort needs >= 2 recordings`

## Correct startup path

The deployment entry point now uses the production path:

1. `load_config()` reads the authoritative `NV_*` startup config from `backend/application_platform/server/config.py`.
2. `build_application(config)` constructs the real `ApplicationPlatformService` and the real FastAPI app from `backend/application_platform/server/factory.py`.
3. The app lifespan runs the single authoritative startup recovery chain:
   - validate the service,
   - run `lifecycle.recover_model(service, provision=...)`,
   - record recovery results in `app.state.startup_report` and `app.state.model_recovery_report`.
4. The app exposes `/livez` and `/readyz` for honest readiness checks.

## Recovery chain

The startup recovery chain is:

- `build_application()`
  - `build_service()` → `ApplicationPlatformService(**kwargs)`
  - `_provision_startup_model()`
    - `lifecycle.recover_model()`
      - `provisioning.provision_model()` (MP-1 deterministic model provisioning)
      - `persistence.ApplicationStateStore` / DBE-4 identity persistence (MP-3)
      - `lifecycle.assess_recovery_readiness()` for `/readyz`

This is the same path documented by the MP-1 / MP-3 architecture references under `backend/application_platform/docs/`.

## Model loading mechanism

The model is not loaded by the legacy cohort bootstrap anymore. The authoritative startup path reconstructs or recovers a usable model context in-process through the application-platform service and recovery lifecycle. That means deployment startup depends on the real production server architecture, not on a pre-existing cohort snapshot.

## Files changed

- `scripts/serve_neurovision.py` — switched from the legacy frontend bootstrap to `load_config()` + `build_application()`.

## Verification

Verified in this workspace with:

- `python scripts/serve_neurovision.py` → `/health` and `/readyz` returned HTTP 200.
- `pytest tests/test_server_entrypoint.py tests/test_mp1_model_provisioning.py tests/test_mp3_model_lifecycle.py -q` → all tests passed.
