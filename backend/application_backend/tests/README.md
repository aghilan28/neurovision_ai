# Application Backend tests

Following the platform convention (and so the architecture-boundary tests scan the
package cleanly), the executable tests for this subsystem live in the **repository-root**
`tests/` directory:

* `tests/test_application_backend.py` — component tests (authentication, sessions, users,
  workflow, API, validation, registry, audit, lineage, reports, boundary, security,
  determinism).
* `tests/test_application_backend_e2e.py` — the full deliverable end to end
  (authenticate → upload → analysis → prediction/confidence/explanation → retrieve),
  plus cross-run determinism.

They run as part of the full suite (`python -m pytest`) and reuse the real P1–P5 services
and the committed EEG fixtures in `tests/fixtures/eeg/` (no replacement systems).

The phase-completion criteria are verified by:

```bash
python -m scripts.verify_productization_p6
```
