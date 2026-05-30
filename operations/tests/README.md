# Operations tests

Following the platform convention, the executable tests for this subsystem live in the
**repository-root** `tests/` directory:

* `tests/test_operations.py` — configuration, environments, container/deployment
  definitions, health checks, logging, monitoring, backup + recovery (incl. tamper
  detection), CI validation, operations validation + reports, the deployable
  upload→prediction pipeline smoke, boundary conditions, and failure conditions.

Tests exercise the **real** P1–P7 systems (no replacement systems). The phase-completion
criteria — including a real container build + run — are verified by:

```bash
python -m scripts.verify_productization_p8
```
