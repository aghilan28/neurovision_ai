# ADR-0001 — V1-P5 Baseline Model Layer + V1-P6 Uncertainty & Calibration Layer

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** V1-P5 + V1-P6
> **Enforces / honors:** AP-1…AP-12, NR-1…NR-15 (esp. AP-2/NR-3 patient-disjoint,
> AP-4/NR-4 uncertainty, AP-3/AP-6/NR-9/NR-10 determinism/reproducibility,
> AP-7/NR-8 boundaries, AP-5/AP-8/NR-11 traceability, AP-9/NR-5 this record)
> **Decision owner:** ML platform engineering (Kiro-assisted, subject to NR-7 human review)

This record captures *why* the V1-P5/V1-P6 implementation is shaped the way it is,
so the rationale survives contributor/agent turnover (NR-14, the Lore Protocol).

---

## 1. Context

The implementation directive for V1-P5 (Baseline Model Layer) and V1-P6
(Uncertainty & Calibration Layer) names V1-P1…V1-P4 (EEG Data Foundation, Signal
Processing, Dataset Intelligence, Evaluation Foundation) as authoritative
prerequisites. On the working branch, the repository contained only the
**V0-P1 + V0-P2** deliverables (constitution + architecture docs and per-directory
boundary contracts); no executable V1 code was present.

We therefore had to: (a) deliver the V1-P5/P6 scope, (b) make it executable and
testable end to end, and (c) do so **without violating any V0 architectural law**
— in particular the acyclic import DAG (NR-8) and patient-disjoint/uncertainty/
determinism invariants.

## 2. Decisions

### D1 — Build minimal, contract-faithful foundations for the absent prior phases
We implemented **minimal but real** `preprocessing/`, `datasets/`, and
`evaluation/` modules sufficient to execute the full V1 pipeline. These honor
their V0-P2 boundary contracts exactly (e.g. `preprocessing` imports nobody
internal; `datasets` imports only `preprocessing`; `evaluation` imports
`ml`/`datasets`/`preprocessing`). They are intentionally focused on the
*integration surface* V1-P5/P6 require (deterministic windowing/normalization;
patient-indexed synthetic cEEG + patient-disjoint LOSO splitting; patient-disjoint
metrics + calibration/coverage measurement). When the full V1-P1…P4 deliverables
land, these foundations are extended within the same contracts — never rewritten
(AP-1/NR-6).

**Rationale:** "No isolated implementation" (directive) + NR-12 (don't claim a
later phase's exit criteria on an unvalidated foundation) require a runnable,
patient-disjoint, reproducible pipeline. Stubs that cannot execute would violate
the directive's final-validation criteria.

### D2 — `ml` must never import `evaluation`; benchmarking integrates via a port
NR-8 / the dependency DAG forbid `ml → evaluation` (evaluation imports ml; the
reverse would create a cycle and let models "grade their own homework"). The
directive nonetheless requires `ml/benchmarking` to "integrate directly with the
V1-P4 evaluation framework."

We resolved this with an **inversion of dependency**: `ml/benchmarking` defines
the `EvaluationResult` contract and an `EvaluationPort` protocol. The evaluation
layer (allowed to import `ml`) produces `EvaluationResult`s; the **orchestrator in
`scripts/`** (which may import every layer) wires `ml` and `evaluation` together.
Thus model outputs *do* pass through the evaluation framework, but the ML layer
stays strictly below evaluation in the DAG. `build_benchmark_record` refuses to
register a non-patient-disjoint evaluation (NR-3).

### D3 — `ml/data/` instead of the directive's `ml/datasets/`
The directive lists a `datasets/` subdirectory under `ml/`. A top-level
`datasets/` package already exists (and `ml` imports it). To avoid a confusing
name shadow and protect maintainability (AP-12), the ML dataset adapter is named
**`ml/data/`** and documented as "the directive's `ml/datasets`."

### D4 — Tests live in top-level `tests/`, not `ml/tests`
`tests/README.md`, `MODULE_BOUNDARIES.md`, and `IMPORT_RULES.md` make `tests/` the
authoritative, cross-cutting test location ("the one place permitted to import
everything"). The directive's `ml/tests` and `ml/uncertainty/tests` requirements
are satisfied by subject-matter test files under `tests/` (model contracts,
registry, training validation, lineage, benchmarking, artifacts, determinism,
reproducibility, calibration, conformal, coverage, risk, reliability, boundaries).
Architecture is authoritative over the directive's directory layout per the
conflict-resolution order (Governance integrity first).

### D5 — Pure-NumPy, framework-free, deterministic reference baselines
EEGNet, TCN, and SimpleCNN are implemented as deterministic NumPy feature
extractors (fixed, seeded weights) followed by a *trained* multinomial-logistic
(softmax) head (deterministic full-batch gradient descent). The directive's stated
goal is **reliability, reproducibility, auditability, and uncertainty-awareness —
not peak accuracy**. Pure NumPy guarantees bit-for-bit determinism (AP-3/NR-9) and
reproducibility (AP-6/NR-10) with no heavy dependency or hardware nondeterminism —
exactly the properties a *reference* baseline must have. Future architectures
(deep TCN, Mamba, foundation models) attach at the same `BaseModel` contract and
are compared against these baselines through the same evaluation + benchmark path.

### D6 — Determinism of provenance: content-addressed ids, no wall-clock in hashes
All identifiers (model_version, lineage_id, benchmark_id, run_id) are content
hashes of canonical JSON. `created_at`/training dates are recorded as **non-hashed**
metadata so wall-clock time never perturbs reproducibility (NR-10). Weights are
serialized with a custom deterministic container (not `np.savez`, whose zip headers
embed timestamps), so artifact checksums are reproducible.

### D7 — Synthetic, patient-structured data for V1 execution
A deterministic synthetic cEEG generator (ACNS-aligned classes SZ/LPD/GPD/LRDA/
GRDA/Other, per-patient variability, laterality encoded as structure) lets the
whole stack run and be tested bit-for-bit without distributing protected patient
EEG. Real recordings attach at the same `EEGDataset` contract in later data work.

## 3. Consequences

- The full required deliverable executes with complete traceability:
  Dataset → Preprocessing → Patient-Disjoint Split → Baseline Model → Evaluation →
  Calibration → Conformal → Coverage → Risk → Benchmark Registration.
- The acyclic DAG is preserved and **enforced by tests** (`tests/test_boundaries.py`
  fails the build on any forbidden import; `ml` is proven never to import
  `evaluation`).
- Every model and uncertainty artifact is versioned, registered, lineage-tracked,
  checksummed, and reproducible.
- No V0 invariant is weakened; no architecture rewrite occurred (AP-1/NR-6).

## 4. Scope guard (what we deliberately did NOT build — NR-13)

Streaming/real-time inference, monitoring, hospital/FHIR integration, multi-user
systems, deployment infrastructure, and any V2/V3/V4 capability are **out of V1
scope** and were not implemented. The uncertainty layer includes only an inert,
documented `operational_risk_hook` seam for future (V2+) operational risk — no
operational logic.

## 5. Follow-ups / recorded debt (NR-2)

- When the authoritative V1-P1…P4 deliverables land, reconcile these minimal
  foundations with them by **extension** (not rewrite); re-point `ml`/`evaluation`
  at the richer implementations behind the same contracts.
- Real-EEG dataset adapters should populate `EEGDataset` without changing its
  contract or the patient-disjoint split semantics.

These items are tracked as low-risk, recorded debt with a clear repayment path;
none is hidden (NR-2).
