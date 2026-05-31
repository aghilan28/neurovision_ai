# Clinical Validation tests

Following the platform convention, the executable tests live in the repository-root `tests/`:

* `tests/test_clinical_validation.py` — benchmarking (incl. sensitivity/specificity),
  calibration, reliability (repeatability/reproducibility/cross-run/cross-dataset/failure
  modes), the evidence registry, the comparison engine, readiness, audit/lineage integration,
  reports, schemas, cross-run determinism, and boundary/orphan/invalid conditions.
* `tests/test_clinical_validation_e2e.py` — the full deliverable (benchmark → evaluate →
  reliability → calibration → evidence → trace → score) over the real DRP-1 datasets / DRP-2
  models, the evidence chain reaching the patient, and the honest-evidence statement.
* `tests/_drp6_helpers.py` — builds a real P1→P2→P3 feature cohort (no replacement systems).

Tests drive the **real** DRP-2 production models + the shared `ImmutableAuditLog` + the shared
`ml.lineage` tracker. Criteria are verified by:

```bash
python -m scripts.verify_drp6_clinical_validation
```
