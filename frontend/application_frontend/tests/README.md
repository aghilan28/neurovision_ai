# Application Frontend tests

Following the platform convention (and so the architecture-boundary tests scan the
package cleanly), the executable tests for this subsystem live in the **repository-root**
`tests/` directory:

* `tests/test_application_frontend.py` — component tests (auth/registration UI, dashboard,
  uploads, analysis workflow, predictions, reports, state management, validation, boundary
  conditions, error states, session expiration).
* `tests/test_application_frontend_e2e.py` — the full deliverable end to end
  (log in → upload → analyse → prediction → confidence → explanation → reports), plus
  cross-run determinism and the full-API-surface exercise.

Every test drives the **real** backend (`ApplicationBackendService` / `ApplicationAPI`)
through `scripts.application_frontend_gateway.LiveBackendGateway` — **no fake contracts**.

The phase-completion criteria are verified by:

```bash
python -m scripts.verify_productization_p7
```
