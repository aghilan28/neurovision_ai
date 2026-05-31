# Validation tests

Following the platform convention, the executable tests for this subsystem live in the
**repository-root** `tests/` directory:

* `tests/test_validation.py` — benchmarking, model/pipeline validation, robustness,
  reliability, reproducibility (within + cross instance), calibration, drift, scorecards,
  reporting, determinism, validation integrity, and the one-way boundary.

Tests exercise the **real** P1–P8 systems (no fake substitutes). The phase-completion
criteria are verified by:

```bash
python -m scripts.verify_productization_p9
```
