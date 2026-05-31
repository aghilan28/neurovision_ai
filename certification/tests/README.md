# Certification tests

Following the platform convention, the executable tests for this subsystem live in the
**repository-root** `tests/` directory:

* `tests/test_certification.py` — evidence collection, end-to-end certification, product +
  deployment readiness audits, risk analysis, gap analysis, scorecards, the decision engine
  (evidence-based + pure), reporting, evidence integrity, and the one-way boundary.

Tests exercise the **real** P1–P9 systems (no substitutes). The phase-completion criteria and
the final verdict are produced by:

```bash
python -m scripts.verify_productization_p10
```
