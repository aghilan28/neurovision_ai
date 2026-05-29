# Metrics (V1-P4)

All metrics are implemented in **pure NumPy** (no third-party ML library), are
deterministic, and each result carries an **input fingerprint** (metric lineage).

## Implemented
| Metric | Output | Notes |
|--------|--------|-------|
| `accuracy` | scalar | fraction correct |
| `balanced_accuracy` | scalar | mean per-class recall (imbalance-robust) |
| `precision_macro` / `recall_macro` / `f1_macro` | scalar | macro-averaged |
| `precision_recall_per_class` | per-class | precision/recall/F1/support + macro |
| `sensitivity_specificity` | per-class | binary sensitivity & specificity |
| `confusion_matrix` | matrix | counts with explicit label order |
| `auroc` | scalar | rank-based (Mann-Whitney U), tie-aware; `None` if one class |
| `auprc` | scalar | average precision (area under PR); `None` if no positives |

Metrics are registered in a `MetricRegistry` with metadata (kind, version, inputs,
output, value range). `compute_suite` computes several at once and **skips
placeholders** by default.

## Placeholders (registered, not computed — NR-13)
`expected_calibration_error` and `coverage` are **placeholders**: their contracts
and names are reserved, but computation is owned by the **future uncertainty
(Conformal Prediction) phase**. Invoking them raises `CalibrationNotAvailable`.
"Future clinical metrics" (e.g. alarm rate) are likewise deferred.

## Why no scikit-learn
Keeping metrics dependency-free (NumPy only) preserves the minimal, pinned
dependency surface and full determinism/auditability (consistent with the V1 data
& DSP foundations). The formulas are standard and unit-tested against known values.
