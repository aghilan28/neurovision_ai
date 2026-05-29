# DEPENDENCY REGISTRY

> **Document type:** AI Operating System (V0-P4) · **Tier 3 (live)**
> **Status:** Living — the authoritative record of what depends on what.
> **Owner:** Founder · **Kept current by:** the active contributor
> **Update procedure:** Any new/changed dependency is an **A2+ change** (RFC→ADR) and is recorded here in the same change set (NR-2/NR-5). Log changes ([`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md)).
> **Last updated:** V0-P4
> **Canonical module graph:** [`../docs/architecture/DEPENDENCY_GRAPH.md`](../docs/architecture/DEPENDENCY_GRAPH.md) · **Rules:** [`../docs/architecture/IMPORT_RULES.md`](../docs/architecture/IMPORT_RULES.md)

This registry tracks all dependency classes. **Silent dependency changes are a
named AI failure mode** (AI_Governance §5.6); recording them here is the defense.
The actual module-import graph is reconciled against this registry during
architecture audits — any unrecorded edge is **architecture drift**.

---

## 1. Module (internal) Dependencies — *authoritative edges*

Mirrors the acyclic graph (leaf-first). **No edge may exist that is not listed
here**; adding an edge requires an ADR (Architecture_Governance §2).

| Module | May depend on | Must NOT depend on |
|--------|---------------|--------------------|
| `preprocessing/` | **(nobody internal)** | everything internal |
| `datasets/` | `preprocessing/` | `ml`, `evaluation`, `backend`, `frontend`, infra |
| `ml/` | `preprocessing/`, `datasets/` | `evaluation`, `backend`, `frontend`, infra |
| `evaluation/` | `ml/`, `datasets/`, `preprocessing/` | `backend`, `frontend`, infra |
| `backend/` | `ml/`, `evaluation/`, `datasets/`, `preprocessing/` | `frontend`, infra (code import) |
| `frontend/` | **backend via API only** (no code import) | all domain modules, infra |
| `deployment/` | tooling/config (+ `tools/`) | domain modules (code import) |
| `monitoring/` | telemetry contracts (+ `tools/`) | domain modules (code import) |
| `.gcc/` | reads all (inspection) (+ `tools/`) | being imported by any production module |
| `tests/` | **any** module | being imported by production code |
| `tools/`, `scripts/` | modules as needed | being imported by production code |

**Acyclicity:** topological order `preprocessing → datasets → ml → evaluation →
backend → frontend`; all edges point backward in this order ⇒ DAG.

## 2. Version Dependencies

| Version | Depends on (must be satisfied first) |
|---------|--------------------------------------|
| V1 | V0 exit criteria (NR-12) |
| V2 | V1 exit criteria |
| V3 | V2 exit criteria |
| V4 | V3 exit criteria |

Build order **within** V1 (leaf-first): `preprocessing` → `datasets` →
`evaluation`/`ml` (see [`ROADMAP_STATUS.md`](./ROADMAP_STATUS.md)).

## 3. External Dependencies (third-party)

> **Current state (V0):** there is **no application code**, therefore **no pinned
> third-party application dependencies yet.** Categories are reserved so they are
> recorded the moment they are introduced (each via ADR).

| Category | Status | When introduced | Constraint |
|----------|--------|-----------------|------------|
| Numerical / DSP libs (for `preprocessing/`) | none yet | V1 | Pinned; deterministic; reproducible (AP-3/AP-6). |
| Data/IO libs (for `datasets/`) | none yet | V1 | Pinned; leakage-safe handling. |
| ML libs (for `ml/`) | none yet | V1 | Pinned; must support reproducibility + UQ. |
| Stat/eval libs (for `evaluation/`) | none yet | V1 | Pinned; reproducible metrics. |
| Service/web libs (for `backend/`) | none yet | V2 | Pinned; preserve uncertainty/provenance. |
| UI libs (for `frontend/`) | none yet | V2 | Pinned; faithful uncertainty rendering. |
| Streaming/observability (infra) | none yet | V3 | Pinned; one-way coupling. |
| **No vendor/hardware lock-in** as an architectural assumption | enforced | — | Scope R7. |

**Rule:** every external dependency is **pinned** (version-locked) for
reproducibility; an unpinned dependency is a defect (AP-6).

## 4. Tooling Dependencies

| Tool class | Status | Purpose | Notes |
|------------|--------|---------|-------|
| Git + hosting | active | Version control, PRs, history-as-record | Branch workflow: [`BRANCH_WORKFLOW.md`](./BRANCH_WORKFLOW.md). |
| CI runner | to add | Run GCC checks + tests on PRs | Required by AP-11 ([`NEXT_STATE.md`](./NEXT_STATE.md) §3). |
| GCC check implementation | to build | Mechanize import/boundary/acyclicity + doc-consistency checks | First tooling task; lives under `.gcc/` + `tools/`. |
| Markdown/doc linting | optional | Link/term consistency | Supports Documentation_Governance §8. |

## 5. Future Dependencies (anticipated; not committed)
- Site/domain-adaptation tooling (V4); federated/privacy-preserving training
  (post-V4) — both gated by FUTURE-scope promotion (RFC→ADR) and Scope F4/F5.
- Regulatory/audit export tooling (V4+), built on the existing audit trail (Scope F6).

## 6. Registry Hygiene
- Reconcile §1 against actual imports during every architecture audit
  (Architecture_Governance §10); unrecorded edge ⇒ drift ⇒ stop-and-remediate.
- Every external/tooling dependency entry records **why** it exists and its
  governing ADR once introduced.
- IDs (when needed for tracking a specific dependency decision): `DEP-NNNN`.
