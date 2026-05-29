# V1-P6 — Uncertainty & Calibration Layer (method details)

> **Phase:** V1-P6 · **Status:** Implemented
> **Decision record:** [`../../../.gcc/decisions/ADR-0001-...`](../../../.gcc/decisions/ADR-0001-v1-p5-p6-baseline-models-and-uncertainty.md)

The clinical confidence layer. Each method below is deterministic, versioned, and
reproducible, and its outputs are lineage-tracked and auditable.

---

## 1. Calibration — temperature scaling

A single scalar temperature `T > 0` divides the logits before softmax, fit by
minimizing negative log-likelihood on a **patient-disjoint calibration set**.
Temperature scaling preserves the argmax (accuracy unchanged) while making the
reported confidence honest.

- **Fit:** deterministic coarse log-spaced grid search + golden-section
  refinement (no randomness).
- **Reliability analysis:** Expected Calibration Error (**ECE**), Maximum
  Calibration Error (**MCE**), multiclass **Brier score**, and reliability bins,
  reported **before and after** calibration.
- **Honesty note:** temperature scaling minimizes NLL, not ECE, so post-fit ECE
  can occasionally be marginally higher than pre-fit on a given set; the report
  states this faithfully (`improved` flag) rather than hiding it.

## 2. Conformal prediction — split conformal (LAC)

Nonconformity score for class `k` is `s_k = 1 − p_k` (one minus the calibrated
probability). On the calibration set we take the true-class scores and compute the
finite-sample-corrected quantile

```
qhat = quantile( scores, ceil((n+1)(1−α)) / n )
```

The prediction set for a test window is `{k : 1 − p_k ≤ qhat} = {k : p_k ≥ 1 − qhat}`.

Under exchangeability — guaranteed here because calibration and test sets are
**patient-disjoint** — this yields the marginal coverage guarantee
`P(y ∈ set) ≥ 1 − α`.

`force_nonempty=True` includes the top-1 class whenever a set would be empty. This
only *increases* coverage (the guarantee is preserved) and avoids the clinically
awkward "no prediction" output.

## 3. Coverage framework

`CoverageTracker` reports, on the patient-disjoint test set:

- **target** vs **observed** coverage,
- **coverage drift** (observed − target),
- **violations** (windows whose true label is outside the set) and violation rate,
- **per-class coverage** and mean set size,
- a **coverage audit** with a reliability verdict (observed ≥ target − tolerance)
  and an audit signature for traceability.

## 4. Risk framework

`RiskAssessor` derives, per window, an explainable risk score:

```
risk = (1 − calibrated_top1_confidence) + size_weight · ambiguity(set_size)
```

- **Confidence bands:** low / medium / high (thresholded).
- **Abstain / escalate:** a window is flagged for human review when risk exceeds
  the abstain threshold **or** its conformal set is not a singleton — consistent
  with decision-support, never autonomy (Scope O5/R1).
- **Clinical risk profiles:** per-class mean risk/confidence and abstain counts.
- **Future operational risk hook:** an inert seam (`operational_risk_hook`) for
  V2+ operational signals; it carries no operational logic in V1.

## 5. Reliability analysis (artifacts as data)

Reliability diagrams, calibration tables, confidence histograms, per-class
prediction-confidence profiles, and risk profiles — all JSON-able so they are
reproducible, versioned, and renderable by any later presentation layer without
coupling this layer to plotting.

## 6. Governance: registry · lineage · validation · reports

- **Uncertainty registry** tracks calibration/conformal/coverage/risk/model/
  dataset/evaluation/artifact/lineage versions; no uncertainty artifact exists
  outside it.
- **Uncertainty lineage** is content-addressed with parents linking back through
  evaluation to model training — every uncertainty output is traceable end-to-end.
- **Validation** checks: calibration measured · conformal assessed · calibration
  set patient-disjoint · coverage reliable · lineage integrity · clinical
  completeness (NR-4).
- **Reports** (all reproducible, version/lineage tagged): calibration · conformal ·
  coverage · risk · summary · audit.

## 7. Integration & boundary

`ml/uncertainty` imports only `ml` submodules + foundations and **never imports
`evaluation`** (NR-8). The evaluation layer independently *verifies* calibration
and coverage; the orchestrator (`scripts/run_pipeline.py`) composes model →
evaluation → uncertainty → benchmark with full traceability.
