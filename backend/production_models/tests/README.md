# Production Models tests

Following the platform convention, the executable tests live in the repository-root
`tests/`:

* `tests/test_production_models.py` — architecture framework, training, benchmarking
  (ROC-AUC/PR-AUC + timings excluded from signatures), evaluation analyses, readiness,
  registry/audit/lineage integration, schemas, cross-run determinism, and
  boundary/invalid/missing conditions.
* `tests/test_production_models_e2e.py` — the full deliverable (train → evaluate →
  benchmark → compare → score readiness → trace → audit), DRP-1 dataset-registration
  integration, all nine reports, corrupted-metadata handling, and the not-reproducible →
  QUARANTINED path.
* `tests/_drp2_helpers.py` — builds a real P1→P2→P3 feature cohort over the committed EEG
  fixtures (no replacement systems).

Tests drive the **real** model-foundation building blocks and feature assets. Criteria are
verified by:

```bash
python -m scripts.verify_drp2_production_models
```
