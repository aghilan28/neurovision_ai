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
