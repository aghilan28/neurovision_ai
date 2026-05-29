# `ml/` — ML Layer

> **Layer:** ML Layer
> **Directory README type:** Repository Architecture Foundation (V0-P2)
> **Status (V0):** Boundary contract defined; **no code yet** (correct for V0).
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
