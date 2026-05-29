# `ml/` — ML Layer

> **Layer:** ML Layer
> **Directory README type:** Repository Architecture Foundation (V0-P2)
> **Status (V0):** Boundary contract defined.
> **Status (V1-P5 + V1-P6):** **Implemented** — baseline models + uncertainty layer (see "V1 Implementation" below).
> **Governing docs:** AP-4 (uncertainty-aware), AP-2 (patient-disjoint), AP-5 (traceability), AP-10 (domain shift), NR-4, [`../docs/architecture/IMPORT_RULES.md`](../docs/architecture/IMPORT_RULES.md)

Owns the **models and inference** that detect and characterize seizures and the
IIC. Every output this layer produces must carry **calibrated uncertainty** and
**provenance**.

---

## Purpose
Provide model definitions, training, and **uncertainty-aware inference** for
detecting SZ and the IIC patterns (LPD, GPD, LRDA, GRDA, Other) from preprocessed
EEG.

## Responsibilities
- Define model architectures (e.g. sequence models such as **Mamba**-class
  state-space models) and training procedures.
- Produce inference outputs with **calibrated uncertainty** (e.g. Conformal
  Prediction) and the ability to **abstain/escalate** (AP-4, NR-4).
- Attach **provenance** to outputs: model version + the preprocessing version of
  its inputs (AP-5, NR-11).
- Cooperate with `evaluation/` so all reported performance is **patient-disjoint**
  (AP-2) and shift-aware (AP-10).

## Allowed dependencies
- ✅ `preprocessing/` (deterministic transforms).
- ✅ `datasets/` (patient-level, leakage-safe data).
- ✅ Pinned third-party ML libraries.

## Forbidden dependencies
- ❌ `backend/`, `frontend/`, `monitoring/`, `deployment/` (NR-8).
- ❌ `evaluation/` — **evaluation imports `ml`, not the reverse** (prevents the
  "grade your own homework" cycle; keeps the graph acyclic).
- ❌ Emitting outputs without calibrated uncertainty (NR-4) or without provenance (NR-11).

## Future responsibilities
- **V1:** baseline detection/classification models + calibrated UQ; reproducible training.
- **V3:** incremental/streaming inference reusing the same preprocessing + UQ machinery.
- **V4:** model governance/versioning suitable for hospital deployment and audit.

## Version ownership
- **Introduced/owned from V1.** Contract defined in **V0-P2** (this README).

## Examples
- A sequence classifier producing per-window class scores **plus** a conformal
  prediction set with a target coverage.
- An inference call that returns `abstain` when confidence is below the clinical
  threshold, routing the case to human review.
- A model card (in `docs/`) describing training data provenance and validation regime.

## Boundary rules
- May import `preprocessing/` and `datasets/`; must **not** import `evaluation/`,
  `backend/`, or `frontend/` (see the acyclic
  [dependency graph](../docs/architecture/DEPENDENCY_GRAPH.md)).
- **Uncertainty is mandatory** on clinical outputs (NR-4); bare labels are not a
  valid clinical output.
- Does not curate data (`datasets/`), compute final metrics (`evaluation/`), or
  serve clients (`backend/`).
- Generalization claims require shift-aware evaluation (AP-10, NR-15) performed in
  `evaluation/`.


---

## V1 Implementation (V1-P5 Baseline Models + V1-P6 Uncertainty)

> Implemented within the V0-P2 boundary contract above — **extended, not rewritten**
> (AP-1). Decision record: [`../.gcc/decisions/ADR-0001-v1-p5-p6-baseline-models-and-uncertainty.md`](../.gcc/decisions/ADR-0001-v1-p5-p6-baseline-models-and-uncertainty.md).

### Subsystems

```
ml/
├── schemas/        typed, versioned model I/O contracts
├── models/         SimpleCNN · EEGNet · TCN (+ factory: the only model constructor)
├── data/           ML dataset adapter (the directive's "ml/datasets"; see ADR-0001 D3)
├── training/       deterministic training pipeline · config · manifest · report
├── validation/     the 7 mandated training-validation checks
├── registry/       model registry (no model exists outside it)
├── artifacts/      deterministic, checksummed artifact store
├── lineage/        version bundles + content-addressed lineage graph
├── benchmarking/   benchmark records + registry; EvaluationPort (ml never imports evaluation)
├── uncertainty/    V1-P6 — calibration · conformal · coverage · reliability · risk (+ registry/lineage/validation/reports)
├── provenance.py   hashing / content-addressing / canonical-JSON IO
└── version.py      all version constants
```

### What it guarantees
- **Reproducible reference baselines** (EEGNet, TCN, SimpleCNN) — pure NumPy,
  deterministic, framework-free. Future models are compared against these.
- **Governed by construction:** every model is versioned, registered, lineage-
  tracked, checksummed, and trained through one validated pipeline.
- **Uncertainty-aware:** calibrated probabilities + conformal prediction sets with
  a coverage guarantee + risk/abstain — a `Prediction` is *clinically complete*
  only when calibrated uncertainty is attached (NR-4).
- **Patient-disjoint or it didn't happen (NR-3):** benchmarking refuses any
  non-patient-disjoint evaluation.

### Where things are documented
- Baseline models & training/registry/lineage/benchmarking design + model cards:
  [`docs/V1_P5_BASELINE_MODELS.md`](./docs/V1_P5_BASELINE_MODELS.md)
- Uncertainty methods: [`uncertainty/README.md`](./uncertainty/README.md) and
  [`uncertainty/docs/V1_P6_UNCERTAINTY.md`](./uncertainty/docs/V1_P6_UNCERTAINTY.md)

### Run the end-to-end pipeline
```bash
python -m scripts.run_pipeline            # Dataset→Preprocess→Split→Model→Eval→
                                          # Calibration→Conformal→Coverage→Risk→Benchmark
python -m pytest                          # full test suite (incl. boundary/determinism gates)
```

### Boundary reminder (unchanged from V0)
`ml` imports **only** `preprocessing` and `datasets`. It **never** imports
`evaluation` (evaluation imports ml — no cycle, NR-8). Cross-layer orchestration
that needs both lives in `scripts/`. This is enforced by `tests/test_boundaries.py`.
