# DEPENDENCY GRAPH

> **Document type:** Repository Architecture Foundation (V0-P2)
> **Status:** Authoritative
> **Enforces:** Principle **AP-7** (modularity/boundaries); Rule **NR-8** (no boundary/import violations)
> **Companion docs:** [`LAYERED_ARCHITECTURE.md`](./LAYERED_ARCHITECTURE.md), [`IMPORT_RULES.md`](./IMPORT_RULES.md), [`MODULE_BOUNDARIES.md`](./MODULE_BOUNDARIES.md)
> **Mechanized by:** the Governance & Context Control layer ([`../../.gcc/README.md`](../../.gcc/README.md))

This document defines the **complete, authoritative graph of allowed
dependencies** between modules. The graph is **directed and acyclic (a DAG)**.
Every edge here must match the per-directory READMEs and
[`IMPORT_RULES.md`](./IMPORT_RULES.md) exactly; any disagreement is a consistency
defect to fix.

---

## 1. Nodes

| Node | Layer / role | In production graph? |
|------|--------------|----------------------|
| `preprocessing/` | DSP (leaf) | ✅ |
| `datasets/` | Data access | ✅ |
| `ml/` | ML | ✅ |
| `evaluation/` | Validation | ✅ |
| `backend/` | Application | ✅ |
| `frontend/` | Presentation | ✅ |
| `deployment/` | Infrastructure | ⚙️ wraps (one-way) |
| `monitoring/` | Infrastructure | ⚙️ observes (one-way) |
| `.gcc/` | Governance (cross-cutting) | 🔒 governs, imported by none |
| `docs/` | Context (cross-cutting) | 🔒 imported by none |
| `tests/` | Test-only | 🧪 imports all, imported by none |
| `tools/`, `scripts/` | Dev/ops support | 🛠️ imported by no production code |

---

## 2. Allowed Imports (the DAG)

Each row lists exactly what a module **may** import. Anything not listed is
**forbidden** (default-deny).

| Module | May import (internal) | May import (external) |
|--------|-----------------------|-----------------------|
| `preprocessing/` | **(nobody)** | pinned numeric/DSP libs |
| `datasets/` | `preprocessing/` | pinned I/O/array libs |
| `ml/` | `preprocessing/`, `datasets/` | pinned ML libs |
| `evaluation/` | `ml/`, `datasets/`, `preprocessing/` | pinned numeric/stat libs |
| `backend/` | `ml/`, `evaluation/`, `datasets/`, `preprocessing/` | pinned service libs |
| `frontend/` | **(no internal module)** — backend **via API only** | pinned UI libs |
| `deployment/` | **(no domain imports)** — references artifacts | build/orchestration tooling |
| `monitoring/` | **(no domain imports)** — shared telemetry contracts only | observability tooling |
| `.gcc/` | reads all (inspection); may use `tools/` | check/CI tooling |
| `tests/` | **any** module | test frameworks |
| `tools/` | modules as needed (analysis) | tooling libs |
| `scripts/` | modules (orchestration via public APIs) | CLI/automation libs |

> **Default-deny principle.** If an edge is not explicitly allowed above, it is
> forbidden. New edges require a recorded governance decision (Rule **NR-5**).

---

## 3. Dependency Flow Diagram

```
                         ┌─────────────┐
                         │  frontend/  │  (Presentation)
                         └──────┬──────┘
                                │  API only (NOT a code import)
                                ▼
                         ┌─────────────┐
                         │   backend/  │  (Application)
                         └──┬───┬───┬──┬┘
              ┌─────────────┘   │   │  └───────────────┐
              ▼                 ▼   ▼                  ▼
        ┌───────────┐     ┌─────────┐  ┌───────────┐  (backend also → preprocessing)
        │evaluation/│     │   ml/   │  │ datasets/ │
        └──┬──┬──┬──┘     └──┬───┬──┘  └─────┬─────┘
           │  │  │           │   │           │
           │  │  └───────────┼───┼───────────┘  (evaluation → datasets)
           │  │              │   └──────────────┐ (ml → datasets)
           │  └──────────────┼──────────────────┤ (evaluation → ml)
           ▼                 ▼                   ▼
                       ┌───────────────┐
                       │ preprocessing/│  (DSP — leaf, imports nobody)
                       └───────────────┘

  Infrastructure (one-way, wraps the stack):
     deployment/  ──packages/deploys──►  [the stack]      (not imported by stack)
     monitoring/  ◄──telemetry via contracts── backend/, ml/ (not imported by stack)

  Cross-cutting (imported by nobody):
     .gcc/   governs/inspects all · docs/  records intent (Lore Protocol)
```

**Acyclicity check (topological order, leaf → root):**
`preprocessing` → `datasets` → `ml` → `evaluation` → `backend` → `frontend`.
Every allowed edge points from a later node to an earlier node in this order, so
**no cycle is possible.** (Infrastructure, governance, context, and test/tooling
nodes are outside the production cycle by construction.)

---

## 4. Forbidden Imports (high-value examples)

These are explicitly forbidden; each is an **architecture-drift** violation
(Rule **NR-8**). The full enumeration with code-style examples is in
[`IMPORT_RULES.md`](./IMPORT_RULES.md).

| Forbidden edge | Why it is forbidden |
|----------------|---------------------|
| `frontend → ml` / `→ preprocessing` / `→ datasets` / `→ evaluation` | Presentation must not touch domain logic; talks to backend via API only. |
| `frontend → backend` (code import) | Even backend must be reached over the API boundary, not imported. |
| `preprocessing → anything internal` | The DSP leaf must stay dependency-free and deterministic. |
| `ml → evaluation` | Would create a cycle and let models "grade their own homework." |
| `ml → backend` / `ml → frontend` | Upward dependency; inverts the layering. |
| `datasets → ml` / `datasets → evaluation` | Upward dependency; data access must stay below ML/eval. |
| any module `→ tests` / `→ tools` / `→ scripts` | Support code must never become a production dependency. |
| any domain module `→ monitoring` / `→ deployment` (code import) | Infrastructure observes/deploys; it is not a code dependency of domain logic. |
| any module `→ .gcc` | Governance is cross-cutting and imported by nobody. |

---

## 5. Future Extension Points

The graph is **stable in shape** across V0 → V4; it is **populated**, not
re-drawn. Permitted ways to extend:

- **Add a module *below* an existing one** (a new leaf-ward dependency), e.g. a
  shared, dependency-light "contracts/types" module that `preprocessing` and others
  may import — provided it introduces no cycle.
- **Add a sibling at the same layer** with the same upward/downward constraints
  (e.g. a second evaluation strategy under the `evaluation/` boundary).
- **Add infrastructure** (under `deployment/`/`monitoring/`) that remains one-way.

Forbidden extensions:
- Any edge that creates a **cycle**.
- Any **upward** edge (lower layer importing a higher layer).
- Any edge that makes `frontend` import a domain module, or `preprocessing` import
  anything internal.
- Any edge that makes production code depend on `tests/`, `tools/`, `scripts/`,
  `monitoring/`, `deployment/`, or `.gcc/`.

**Every new edge requires a recorded governance decision** (Rule **NR-5**) and is
validated by the Governance layer before it is allowed to exist.

---

## 6. Dependency Rationale (why the edges are what they are)

- **`preprocessing` is the leaf** so the deterministic foundation (AP-3) cannot be
  contaminated by higher-level concerns; everything above inherits reproducibility.
- **`datasets → preprocessing`** so data is delivered model-ready while keeping the
  patient-disjoint invariant (AP-2) at the data layer.
- **`ml → {preprocessing, datasets}`** so models consume deterministic, leakage-safe
  inputs and nothing higher.
- **`evaluation → {ml, datasets, preprocessing}` (and *not* `ml → evaluation`)**
  so validation can grade models without forming a cycle or a conflict of interest.
- **`backend` over the domain modules** so orchestration and the audit trail
  (AP-5/AP-8) live in one place that preserves uncertainty (AP-4).
- **`frontend` via API only** so the presentation layer can never smuggle domain
  logic and can never drop uncertainty unnoticed (AP-4, NR-8).
- **Infrastructure one-way** so deploying/observing the system never becomes a
  hidden runtime dependency of it.
- **Governance/Context cross-cutting and import-free** so they can police and
  document the whole system without being entangled in it (AP-11).

---

## 7. Relationship To Other Documents
- Conceptual basis: [`LAYERED_ARCHITECTURE.md`](./LAYERED_ARCHITECTURE.md).
- Rule-level detail + examples: [`IMPORT_RULES.md`](./IMPORT_RULES.md).
- Per-module contracts: [`MODULE_BOUNDARIES.md`](./MODULE_BOUNDARIES.md).
- Enforcement: [`../../.gcc/README.md`](../../.gcc/README.md); checks in `tests/`.
