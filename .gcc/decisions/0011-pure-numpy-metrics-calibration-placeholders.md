# DR-0011 · Pure-NumPy metrics; calibration/clinical metrics are placeholders

- **Status:** Accepted · **Phase:** V1-P4 · **Date:** caller-supplied

## Context
The evaluation foundation needs classification + ranking metrics now, plus a
*place* for calibration/coverage and clinical metrics that belong to the **future**
uncertainty/clinical phases. It must not pull in a heavy ML dependency or pre-empt
out-of-scope work (NR-13).

## Decision
- Implement all V1 metrics (accuracy, precision/recall/F1, balanced accuracy,
  sensitivity/specificity, confusion matrix, AUROC, AUPRC) in **pure NumPy**,
  deterministic and unit-tested against known values. No scikit-learn.
- Register **calibration** (`expected_calibration_error`, `coverage`) and clinical
  metrics as **placeholders**: their names/contracts are reserved and discoverable,
  but invoking them raises `CalibrationNotAvailable`. Suites skip placeholders.

## Alternatives considered
1. **Depend on scikit-learn** — adds a large pinned dependency for standard
   formulas; conflicts with the minimal, fully-owned dependency surface (DR-0002).
   Rejected.
2. **Implement calibration now** — would pre-empt the future uncertainty
   (Conformal Prediction) phase and risk an out-of-scope design. Rejected (NR-13).

## Consequences
- Minimal dependency surface; deterministic, auditable metrics.
- The framework already *knows about* calibration/clinical metrics, so they slot in
  later without reshaping (AP-1).

## Rules / principles invoked
AP-3/AP-6 (determinism/reproducibility), AP-12 (long-term cost), NR-13 (stay in
scope), DR-0002 (pinned deps).
