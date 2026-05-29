# MODULE BOUNDARIES

> **Document type:** Repository Architecture Foundation (V0-P2)
> **Status:** Authoritative
> **Enforces:** Principle **AP-7**; Rule **NR-8**
> **Companion docs:** [`LAYERED_ARCHITECTURE.md`](./LAYERED_ARCHITECTURE.md), [`DEPENDENCY_GRAPH.md`](./DEPENDENCY_GRAPH.md), [`IMPORT_RULES.md`](./IMPORT_RULES.md)
> **Per-directory detail:** each module's own `README.md`

This document defines the **boundary contract** for every module: its
**ownership**, **responsibilities**, **inputs**, **outputs**, **dependencies**,
and **forbidden actions**. These contracts must agree with the per-directory
READMEs, the [dependency graph](./DEPENDENCY_GRAPH.md), and the
[import rules](./IMPORT_RULES.md). Where any two disagree, it is a consistency
defect to fix.

---

## Boundary contract template
Each module below is specified as:
**Ownership · Responsibilities · Inputs · Outputs · Dependencies · Forbidden actions.**

---

## `frontend/` — Presentation
- **Ownership:** the clinician-facing experience (V2+).
- **Responsibilities:** render detections/IIC + **uncertainty**; support review/triage; surface provenance references.
- **Inputs:** backend **API responses** (over the network).
- **Outputs:** clinician-facing views/interactions; API requests.
- **Dependencies:** backend **API only** (no internal code imports).
- **Forbidden actions:** importing any domain module (NR-8); hiding/flattening uncertainty (NR-4); embedding DSP/ML/data/eval logic.

## `backend/` — Application
- **Ownership:** orchestration, API surface, audit trail (V2+).
- **Responsibilities:** compose `ml`/`evaluation`/`datasets`/`preprocessing` into use cases; **preserve uncertainty + provenance**; build/maintain the audit trail; expose API contracts.
- **Inputs:** API requests; outputs of the domain modules.
- **Outputs:** API responses carrying detections + uncertainty + provenance references; audit records; runtime telemetry (emitted to monitoring).
- **Dependencies:** `ml`, `evaluation`, `datasets`, `preprocessing`.
- **Forbidden actions:** importing `frontend` (NR-8); dropping/altering uncertainty (NR-4); producing untraceable outputs (NR-11); re-implementing DSP/ML/eval logic.

## `ml/` — ML
- **Ownership:** models and uncertainty-aware inference (V1+).
- **Responsibilities:** define/train models (e.g. Mamba-class); produce inference with **calibrated uncertainty** + **abstain/escalate**; attach model + preprocessing provenance.
- **Inputs:** preprocessed, patient-indexed data from `datasets/`/`preprocessing/`.
- **Outputs:** predictions **with uncertainty** and provenance; trained model artifacts (versioned).
- **Dependencies:** `preprocessing/`, `datasets/`.
- **Forbidden actions:** importing `evaluation`/`backend`/`frontend` (NR-8, no cycle); emitting bare labels as clinical output (NR-4); claiming generalization without shift-aware evaluation (NR-15).

## `preprocessing/` — DSP (leaf)
- **Ownership:** deterministic signal processing (V1+).
- **Responsibilities:** filtering, resampling, montage handling, windowing, normalization; emit the **preprocessing version** as provenance.
- **Inputs:** raw EEG signal + pinned parameters.
- **Outputs:** deterministic, versioned, model-ready signal + version tag.
- **Dependencies:** **none internal** (pinned third-party numerics only).
- **Forbidden actions:** importing any internal module (NR-8); any nondeterminism on the production path (NR-9); loading datasets / running models / serving.

## `datasets/` — Data Access & Curation
- **Ownership:** patient-level, leakage-safe data access (V1+).
- **Responsibilities:** catalog recordings by **patient ID** + metadata (site/montage); make **patient-disjoint (LOSO)** splitting the default; deliver preprocessed, model-ready data with provenance.
- **Inputs:** raw recordings + labels; `preprocessing/` transforms.
- **Outputs:** patient-indexed, preprocessed data; provably patient-disjoint splits.
- **Dependencies:** `preprocessing/`.
- **Forbidden actions:** importing `ml`/`evaluation`/`backend`/`frontend` (NR-8); allowing a patient to span partitions (NR-3); nondeterministic loading (NR-9).

## `evaluation/` — Validation
- **Ownership:** the validity of every reported metric (V1+).
- **Responsibilities:** enforce/assert **patient-disjoint** splits; compute detection metrics; measure **calibration/coverage**; run **held-out-site/montage** (domain-shift) evaluation; record provenance.
- **Inputs:** `ml/` predictions+uncertainty; `datasets/` data/splits; `preprocessing/` transforms.
- **Outputs:** patient-disjoint, reproducible metric reports (with calibration/coverage and shift deltas).
- **Dependencies:** `ml/`, `datasets/`, `preprocessing/`.
- **Forbidden actions:** any non-patient-disjoint evaluation (NR-3, cardinal); being imported by `ml/` (no cycle); presenting in-distribution-only results as general (NR-15).

## `deployment/` — Infrastructure (packaging & deployment)
- **Ownership:** reproducible packaging/deployment (V3/V4).
- **Responsibilities:** pinned reproducible environments; package/deploy services; encode deployment topology for hospital constraints (V4); stay declarative/auditable.
- **Inputs:** built artifacts; configuration.
- **Outputs:** deployable artifacts/environments; deployment configuration.
- **Dependencies:** build/orchestration tooling (+ `tools/`); no domain code imports.
- **Forbidden actions:** importing domain modules into deployment code (NR-8); baking in vendor/hardware lock-in (Scope R7).

## `monitoring/` — Infrastructure (observability & drift)
- **Ownership:** operational observability + drift detection (V3/V4).
- **Responsibilities:** collect telemetry; detect **domain shift / performance drift** (AP-10, NR-15); surface alerts/thresholds; feed the audit trail.
- **Inputs:** telemetry emitted by `backend`/`ml` (via shared contracts).
- **Outputs:** metrics, drift signals, alerts/dashboards.
- **Dependencies:** observability tooling (+ `tools/`); shared telemetry contracts only.
- **Forbidden actions:** importing domain modules (NR-8); being imported by domain modules (no hidden dependency).

## `.gcc/` — Governance (cross-cutting)
- **Ownership:** mechanized governance — boundaries, decisions, audit, drift (V0-P3+).
- **Responsibilities:** enforce import/boundary rules; manage decision records + debt registry + version gates; detect architecture/context drift; operate the Lore Protocol.
- **Inputs:** the whole repository (read/inspect); the `docs/` rules it mechanizes.
- **Outputs:** pass/fail governance checks; decision/debt/gate records; drift reports.
- **Dependencies:** read access to all modules (+ `tools/`).
- **Forbidden actions:** being imported by any production module (NR-8); redefining the constitution (it enforces, `docs/` defines).

## `docs/` — Context (cross-cutting)
- **Ownership:** durable intent, rationale, terminology, architecture (V0+).
- **Responsibilities:** hold the constitution + architecture; be the canonical terminology source; preserve the "why" (Lore Protocol).
- **Inputs:** project decisions and rationale.
- **Outputs:** authoritative documents.
- **Dependencies:** none at runtime.
- **Forbidden actions:** containing executable domain code; contradicting its own canonical definitions.

## `tests/` — Test-only (cross-cutting)
- **Ownership:** executable verification of the rules + guarantees (V0+).
- **Responsibilities:** determinism, patient-disjointness, reproducibility, boundary, and traceability tests; fail the build on violation.
- **Inputs:** any module.
- **Outputs:** pass/fail results; regression coverage.
- **Dependencies:** **any** module; test frameworks.
- **Forbidden actions:** being imported by production code; relaxing a guarantee to pass.

## `tools/` & `scripts/` — Dev/Ops support (cross-cutting)
- **Ownership:** developer utilities (`tools/`) and runnable procedures (`scripts/`) (V0+).
- **Responsibilities:** support governance/consistency (`tools/`); provide thin, reproducible orchestration entry points (`scripts/`).
- **Inputs:** modules (for analysis/orchestration); configuration.
- **Outputs:** utilities/automation; reproducible operational runs.
- **Dependencies:** modules as needed; `tools/` may be used by `scripts/`, `monitoring/`, `deployment/`, `.gcc/`.
- **Forbidden actions:** being imported by any **production** module (NR-8); smuggling forbidden cross-module dependencies; embedding domain logic that belongs in a module.

---

## Boundary-integrity invariants (summary)
1. **One-way, acyclic** domain dependencies (preprocessing → … → frontend).
2. **`preprocessing` imports nobody; `frontend` imports no domain module.**
3. **`evaluation` imports `ml`; `ml` never imports `evaluation`** (no cycle).
4. **Infrastructure (`deployment`/`monitoring`) is one-way**; domain emits telemetry, never imports infra.
5. **Governance/Context (`.gcc`/`docs`) are imported by nobody.**
6. **Support (`tests`/`tools`/`scripts`) is never a production dependency.**
7. Crossing any boundary requires a **recorded governance decision** (NR-5) and is checked by GCC.

## Relationship To Other Documents
- Layer rationale: [`LAYERED_ARCHITECTURE.md`](./LAYERED_ARCHITECTURE.md).
- Edges: [`DEPENDENCY_GRAPH.md`](./DEPENDENCY_GRAPH.md).
- Import-level rules/examples: [`IMPORT_RULES.md`](./IMPORT_RULES.md).
- Enforcement: [`../../.gcc/README.md`](../../.gcc/README.md).
