# `ml/uncertainty/` — Uncertainty & Calibration Layer (V1-P6)

> **Layer:** ML Layer (sub-layer of `ml/`)
> **Status:** Implemented (V1-P6).
> **Governing docs:** AP-4 (uncertainty-aware), AP-5/AP-8 (traceability/audit),
> AP-6 (reproducibility), NR-4 (no clinical output without calibrated uncertainty),
> [`../../.gcc/decisions/ADR-0001-...`](../../.gcc/decisions/ADR-0001-v1-p5-p6-baseline-models-and-uncertainty.md)

The **clinical confidence layer**. It answers not only *"what is the prediction?"*
but *"how confident should we be in this prediction?"* — with calibrated,
conformal, coverage-validated, risk-scored uncertainty that is **versioned,
traceable, reproducible, auditable, and clinically explainable**. No black-box
confidence scores.

---

## Subsystems

| Subsystem | What it does | Key types |
|-----------|--------------|-----------|
| `calibration/` | Deterministic **temperature scaling** + reliability analysis (ECE, MCE, Brier, reliability curves). | `TemperatureScaler`, `CalibrationPipeline`, `CalibrationResult` |
| `conformal/` | **Split conformal prediction** (LAC): prediction sets with a marginal coverage guarantee, fit on a patient-disjoint calibration set. | `SplitConformalPredictor`, `ConformalResult` |
| `coverage/` | **Coverage tracking**: target vs observed, drift, violations, per-class coverage, audit. | `CoverageTracker`, `CoverageResult` |
| `reliability/` | Reliability **diagrams, calibration tables, confidence histograms, prediction-confidence & risk profiles** (as data). | `ReliabilityAnalyzer`, `ReliabilityArtifacts` |
| `risk/` | **Clinical risk scores**, confidence bands, low-confidence alerts, abstain/escalate; inert forward operational-risk hook. | `RiskAssessor`, `RiskResult` |
| `validation/` | Uncertainty **validation** (calibration measured, coverage assessed, calibration set patient-disjoint, lineage integrity, clinical completeness). | `UncertaintyValidator` |
| `registry/` | The **uncertainty registry** — no uncertainty artifact exists outside it. | `UncertaintyRegistry`, `UncertaintyRecord` |
| `lineage/` | Content-addressed **uncertainty lineage** (parents: model-training → evaluation). | `make_uncertainty_lineage` |
| `reports/` | Reproducible **calibration / conformal / coverage / risk / summary / audit** reports. | `build_*_report` |
| `schemas/` | Typed, versioned **result contracts**. | `CalibrationResult`, `ConformalResult`, `CoverageResult`, `RiskResult`, `ReliabilityArtifacts` |
| `pipeline.py` | The deterministic **`UncertaintyPipeline`** that chains all stages. | `UncertaintyPipeline`, `UncertaintyOutput` |

## How it works (one flow)

```
calibration set logits ─┐
                        ├─► TemperatureScaler.fit ──► calibrated probabilities
test set logits ────────┘
            │
            ├─► SplitConformalPredictor (fit on calibration) ──► prediction sets
            │            │
            │            ├─► CoverageTracker ──► observed vs target, drift, violations
            │            └─► RiskAssessor   ──► risk scores, bands, abstain/escalate
            └─► ReliabilityAnalyzer ──► diagrams / tables / histograms / profiles
```

The pipeline operates on **logits/probability arrays** (model-agnostic): the
orchestrator obtains logits via `model.forward_logits(...)`. Calibration and test
sets are **patient-disjoint** (AP-2/NR-3), which is what makes the conformal
coverage guarantee honest.

## Guarantees

- **Calibrated.** Temperature scaling fit by deterministic search on a held-out,
  patient-disjoint calibration set; ECE/MCE/Brier reported before and after.
- **Coverage with a guarantee.** Split conformal yields marginal coverage
  `P(y ∈ set) ≥ 1 − α` under exchangeability (preserved by patient-disjoint
  calibration/test). `force_nonempty` keeps sets clinically usable while only
  *increasing* coverage.
- **Abstain / escalate.** Low-confidence or ambiguous windows are flagged for human
  review — decision-support, never autonomy (Scope O5/R1).
- **Reproducible & auditable.** Every result is versioned, lineage-tracked, and
  serialized as canonical JSON with a stable checksum.

## Boundary

Part of the ML layer; imports only `ml` submodules + the foundations. It **never
imports `evaluation`** (NR-8). The evaluation layer *independently* verifies
calibration/coverage; the orchestrator (`scripts/`) wires the two together.

See [`docs/V1_P6_UNCERTAINTY.md`](./docs/V1_P6_UNCERTAINTY.md) for the method details.
