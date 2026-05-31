# Dataset Integration tests

Following the platform convention, the executable tests live in the repository-root `tests/`:

* `tests/test_dataset_integration.py` — inventory, registration, validation, governance,
  readiness, registry + model-foundation integration, audit, lineage, reports, schemas,
  corrupted/missing metadata, invalid structures, and the boundary.

Tests use the **real** built-in manifests (TUH, CHB-MIT, Temple/TUSZ, Siena, Bonn). Criteria
are verified by:

```bash
python -m scripts.verify_drp1_dataset_integration
```
