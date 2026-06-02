# IMPORT RULES

> **Document type:** Repository Architecture Foundation (V0-P2)
> **Status:** Authoritative
> **Owner:** Founder (Architecture Owner role)
> **Update procedure:** Governance-class change (ADR — [`../governance/Architecture_Governance.md`](../governance/Architecture_Governance.md)); architecture changes require an ADR (NR-5/NR-8).
> **Enforces:** Principle **AP-7**; Rule **NR-8** ("Never violate module boundaries or import rules")
> **Companion docs:** [`DEPENDENCY_GRAPH.md`](./DEPENDENCY_GRAPH.md), [`MODULE_BOUNDARIES.md`](./MODULE_BOUNDARIES.md), [`LAYERED_ARCHITECTURE.md`](./LAYERED_ARCHITECTURE.md)
> **Mechanized by:** [`../../.gcc/README.md`](../../.gcc/README.md)

This document states the import rules **explicitly, with examples.** It is the
practical, line-of-code expression of the [dependency graph](./DEPENDENCY_GRAPH.md).
Examples use a neutral, language-agnostic `import <module>` pseudo-syntax; the
rules apply to whatever languages later versions adopt.

> **Default-deny.** Any import not explicitly allowed below is **forbidden.** When
> in doubt, it is not allowed — open a governance decision (Rule **NR-5**).

---

## 1. The Core Rules (as mandated)

### Rule A — Frontend cannot import Backend, ML, or Preprocessing
The presentation layer reaches the rest of the system **only through the backend
API**, never by importing code (this also forbids importing `datasets/` and
`evaluation/`).

```
# frontend/  (Presentation)
✅ allowed:    call backend over the network    → fetch("/api/detections")
❌ forbidden:  import backend                    # even the backend is API-only
❌ forbidden:  import ml
❌ forbidden:  import preprocessing
❌ forbidden:  import datasets
❌ forbidden:  import evaluation
```

### Rule B — Backend can import ML and Preprocessing (and Datasets, Evaluation)
The application layer orchestrates the domain modules.

```
# backend/  (Application)
✅ allowed:    import ml
✅ allowed:    import preprocessing
✅ allowed:    import datasets
✅ allowed:    import evaluation
❌ forbidden:  import frontend          # never depend upward on Presentation
```

### Rule C — ML can import Preprocessing (and Datasets)
Models consume deterministic, leakage-safe inputs.

```
# ml/  (ML)
✅ allowed:    import preprocessing
✅ allowed:    import datasets
❌ forbidden:  import evaluation        # evaluation imports ml — never the reverse (no cycle)
❌ forbidden:  import backend
❌ forbidden:  import frontend
```

### Rule D — Preprocessing imports nobody
The DSP leaf depends on **no** internal module — only pinned third-party numeric
libraries.

```
# preprocessing/  (DSP — leaf)
✅ allowed:    import <pinned third-party numeric/DSP library>
❌ forbidden:  import datasets
❌ forbidden:  import ml
❌ forbidden:  import evaluation
❌ forbidden:  import backend
❌ forbidden:  import frontend
```

---

## 2. The Complete Rule Set

| From ↓ \ May import → | preproc | datasets | ml | evaluation | backend | frontend | monitoring | deployment | .gcc | tests | tools | scripts |
|----------------------|:------:|:--------:|:--:|:----------:|:-------:|:--------:|:----------:|:----------:|:----:|:-----:|:-----:|:-------:|
| **preprocessing**    | —      | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **datasets**         | ✅     | — | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **ml**               | ✅     | ✅ | — | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **evaluation**       | ✅     | ✅ | ✅ | — | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **backend**          | ✅     | ✅ | ✅ | ✅ | — | ❌ | ❌* | ❌* | ❌ | ❌ | ❌ | ❌ |
| **frontend**         | ❌     | ❌ | ❌ | ❌ | ❌(API only) | — | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **monitoring**       | ❌     | ❌ | ❌ | ❌ | ❌ | ❌ | — | ❌ | ❌ | ❌ | ✅ | ❌ |
| **deployment**       | ❌     | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | — | ❌ | ❌ | ✅ | ❌ |
| **.gcc**             | 🔎 | 🔎 | 🔎 | 🔎 | 🔎 | 🔎 | 🔎 | 🔎 | — | ❌ | ✅ | ❌ |
| **tests**            | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ |
| **tools**            | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | — | ❌ |
| **scripts**          | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | — |

Legend: ✅ allowed · ❌ forbidden · — n/a (self) · 🔎 read-only inspection (not a
runtime code import) · **❌\*** backend does not *import* infra; it **emits
telemetry** to `monitoring/` via shared contracts and is *deployed by*
`deployment/` (data/artifact coupling, not a code import).

> **Reading the table:** rows import columns. The strict lower-triangular shape of
> the domain block (preprocessing…frontend) is the visual proof that the
> production dependency graph is **acyclic** and one-way.

---

## 3. Worked Examples

**✅ Correct — backend orchestrates inference and preserves uncertainty**
```
# backend/service/detect.py  (illustrative)
import preprocessing            # OK (Rule B / C-foundation)
import datasets                 # OK
import ml                       # OK
# ... run inference, KEEP the uncertainty + provenance, expose via API
```

**❌ Violation — frontend importing a model (Rule A, NR-8)**
```
# frontend/views/review.tsx  (illustrative)
import ml                       # ❌ ARCHITECTURE DRIFT — frontend must use the API
```
*Why it fails:* presentation must never embed domain logic; it also risks dropping
uncertainty (NR-4). GCC fails the build.

**❌ Violation — preprocessing importing datasets (Rule D, NR-8)**
```
# preprocessing/filters.py  (illustrative)
import datasets                 # ❌ the DSP leaf must import nobody internal
```
*Why it fails:* it would create an upward dependency and threaten determinism (NR-9).

**❌ Violation — ml importing evaluation (cycle, NR-8)**
```
# ml/model.py  (illustrative)
import evaluation               # ❌ evaluation imports ml; this would form a cycle
```
*Why it fails:* breaks acyclicity and conflates modeling with grading.

**✅ Correct — tests importing everything**
```
# tests/test_boundaries.py  (illustrative)
import frontend, backend, ml, evaluation, datasets, preprocessing  # OK (test-only)
# assert frontend imports no domain module; assert no patient spans splits
```

---

## 4. The Network/API Boundary (frontend ↔ backend)

The single allowed path between presentation and the rest of the system is the
**backend API over the network** — not a code import.

```
frontend  ──HTTP/API request──►  backend  ──(orchestrates ml/eval/datasets/preproc)──►
frontend  ◄──API response with detections + UNCERTAINTY + provenance refs── backend
```

- The frontend **must** render the returned uncertainty faithfully (NR-4).
- The API response **must** carry provenance references so results are traceable
  (NR-11).
- Sharing internal types by importing them across this boundary is **forbidden**;
  the contract is the API schema (a `docs/`/`backend/` artifact), not shared code.

---

## 5. Enforcement

1. **Governance (GCC):** `.gcc/` ([README](../../.gcc/README.md)) encodes this
   table and **fails CI** on any forbidden import (Principle **AP-11**).
2. **Tests:** `tests/` includes boundary tests that scan modules and assert no
   forbidden import exists (e.g. "frontend imports no domain module").
3. **Review:** human reviewers reject PRs that introduce a forbidden edge; new
   edges require a recorded governance decision (Rule **NR-5**).

A violation is **stop-and-remediate**, not a warning.

---

## 6. Relationship To Other Documents
- Graph form: [`DEPENDENCY_GRAPH.md`](./DEPENDENCY_GRAPH.md).
- Per-module contracts: [`MODULE_BOUNDARIES.md`](./MODULE_BOUNDARIES.md).
- Layer rationale: [`LAYERED_ARCHITECTURE.md`](./LAYERED_ARCHITECTURE.md).
- Law: Rule **NR-8** in [`../NON_NEGOTIABLE_RULES.md`](../NON_NEGOTIABLE_RULES.md).
