# Serving Platform tests

Following the platform convention, the executable tests live in the repository-root
`tests/`:

* `tests/test_serving_platform.py` — serving engine + routing (resolution / version
  selection), prediction delivery, lifecycle order, contracts, validation, registry,
  readiness, audit/lineage integration, reports, schemas, cross-run determinism, and
  graceful handling of missing models / invalid requests / unavailable features.
* `tests/test_serving_platform_e2e.py` — the full deliverable for every architecture
  (request → select → infer → respond → trace → audit), coexistence with the DRP-1 dataset
  registrations and the DRP-2 production-model program, corrupted-response handling, and
  idempotent re-serving.
* `tests/_drp3_helpers.py` — builds a real P1→P2→P3 feature cohort over the committed EEG
  fixtures and trains a real model to serve (no replacement systems).

Tests drive the **real** inference foundation + model-foundation models. Criteria are
verified by:

```bash
python -m scripts.verify_drp3_serving_platform
```
