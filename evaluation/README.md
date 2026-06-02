# `evaluation/` — Validation Harness

> **Layer:** Validation module (consumes ML, Datasets, Preprocessing)
> **Directory README type:** Repository Architecture Foundation (V0-P2)
> **Status (V0):** Boundary contract defined; **no code yet** (correct for V0).
> **Governing docs:** AP-2 (patient-disjoint), AP-6 (reproducibility), AP-10 (domain shift), NR-3, NR-15, [`../docs/architecture/IMPORT_RULES.md`](../docs/architecture/IMPORT_RULES.md)

The module that decides **whether a result is real.** It enforces the project's
single most important guarantee: **patient-disjoint validation**. No metric in
NeuroVision AI is trusted unless it comes from here.

---

## Purpose
Produce **defensible, patient-disjoint, reproducible** performance metrics —
including calibration/coverage of uncertainty and robustness under domain shift.

## Responsibilities
- Enforce **patient-disjoint (LOSO-style)** splits **by construction** and assert
  disjointness (AP-2, NR-3).
- Compute detection/classification metrics with per-class breakdown for SZ + IIC.
- Measure **calibration** and, for conformal methods, **empirical coverage** (AP-4).
- Run **held-out-site/montage** evaluation to quantify domain-shift robustness
  (AP-10, NR-15).
- Record provenance so every reported metric is reproducible (AP-6, NR-10).

## Allowed dependencies
- ✅ `ml/` (to obtain predictions/uncertainty).
- ✅ `datasets/` (to obtain patient-indexed data and splits).
- ✅ `preprocessing/` (to reproduce the exact transforms used).
- ✅ Pinned third-party numerical/stat libraries.

## Forbidden dependencies
- ❌ `backend/`, `frontend/`, `monitoring/`, `deployment/` (NR-8).
- ❌ Any evaluation path that is **not** patient-disjoint (NR-3) — this is the
  cardinal violation for this module.
- ❌ Reporting in-distribution-only results as general performance (NR-15).

## Future responsibilities
- **V1:** the patient-disjoint evaluation harness + calibration/coverage + initial
  domain-shift characterization.
- **V2:** evaluation hooks that confirm clinical outputs remain valid end-to-end.
- **V3:** evaluation of streaming inference without introducing leakage.

## Version ownership
- **Introduced/owned from V1.** Contract defined in **V0-P2** (this README).

## Examples
- A LOSO runner that iterates patients as held-out test folds and asserts no
  patient appears in train and test.
- A calibration report comparing stated confidence to realized accuracy.
- A coverage check verifying conformal prediction sets meet their target error rate.
- A held-out-site benchmark reporting the performance delta vs. in-distribution.

## Boundary rules
- Imports `ml/`, `datasets/`, `preprocessing/`; is **never** imported by `ml/`
  (no cycle — see the acyclic [dependency graph](../docs/architecture/DEPENDENCY_GRAPH.md)).
- **Patient-disjointness and reproducibility are mandatory**; violating either is
  a failure metric ([`../docs/PROJECT_OBJECTIVES.md`](../docs/PROJECT_OBJECTIVES.md) §6).
- Does not train models (`ml/`), serve clients (`backend/`), or curate data
  (`datasets/`).


---

## Version 1 (V1-P3 + V1-P4) — Implemented Intelligence & Evaluation

> The boundary contract above (V0-P2) is **unchanged and still authoritative**.
> This section documents the V1-P3/P4 implementation that *populates* this module
> within those boundaries (Principle **AP-1**: extend, never rewrite).

This module now contains two implemented subsystems. **No models are trained here**
(NR-13); predictions are supplied by the caller (a stand-in for future model
outputs) and the module computes *truth*.

### V1-P3 — Dataset Intelligence Layer (`dataset_intelligence/`)
Understand any dataset **without modelling**: profiling, distributions, patient /
channel / recording analysis, class-distribution (annotation→class) analysis,
quality scoring, and **leakage-risk** assessment — assembled into versioned,
reproducible reports. See [`dataset_intelligence/README.md`](./dataset_intelligence/README.md).

### V1-P4 — Evaluation Foundation
The leakage-safe split + metric + benchmark framework that **no model result may
bypass**:

| Path | Responsibility |
|------|----------------|
| [`splits/`](./splits) | Patient-disjoint splits (train/val/test) + LOSO, deterministic & reproducible. |
| [`validation/`](./validation) | **The leakage gate** (patient/session/recording overlap) + evaluation audit. |
| [`metrics/`](./metrics) | Pure-NumPy metrics (accuracy, P/R/F1, balanced acc, sens/spec, AUROC, AUPRC, confusion) + registry; calibration/clinical **placeholders**. |
| [`benchmarking/`](./benchmarking) | Provenance-bound benchmark records (no benchmark without provenance). |
| [`registry/`](./registry) | Discoverable evaluation-run registry (JSON-backed). |
| [`lineage/`](./lineage) | End-to-end evaluation lineage (every metric traceable). |
| [`framework/`](./framework) | The orchestrator: split → gate → metrics → benchmark → lineage → audit → registry. |
| [`reports/`](./reports) | Versioned evaluation/split/leakage/benchmark/audit/summary reports. |

### Minimal usage
```python
from evaluation.splits import patient_disjoint_split, leave_one_subject_out
from evaluation.framework import run_evaluation, Predictions

split = patient_disjoint_split(patients_to_records, base_seed=0,
                               dataset_id="ds-icu", dataset_version="v1")

run = run_evaluation(
    split,
    Predictions(y_true=y_true, y_pred=y_pred, y_score=y_score, labels=(0, 1)),
    dataset_id="ds-icu", dataset_version="v1", preprocessing_version="1.0.0",
)
assert run.approved            # leakage gate passed (NR-3)
assert run.audit["ok"]         # scientifically valid
print(run.benchmark.benchmark_id, run.run_id)
```

### Guarantees
- **Patient-disjoint by construction** (split at the patient level) and **verified**
  by the gate; a leaky split **blocks** the run — no metrics, no benchmark (NR-3).
- **Reproducible:** splits/benchmarks/runs are content-fingerprinted and exclude
  volatile timestamps; metrics carry input fingerprints (AP-6/NR-10).
- **Traceable:** every metric/benchmark ties back through a `VersionBundle`
  (dataset/split/preprocessing/metric/evaluation/[model] versions) and lineage (NR-11).
- **No modelling:** EEGNet/TCN/Mamba/Conformal/inference/training are out of scope (NR-13).

### Dependencies
`datasets`, `preprocessing` (montage compatibility), `numpy`. `ml` is *allowed* but
not imported (no models yet). No `backend`/`frontend`/`monitoring`/`deployment` (NR-8).
