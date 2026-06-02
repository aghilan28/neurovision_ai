# DEPENDENCY MANAGEMENT

> **Document type:** Development Environment Foundation (V0-P7) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Environment Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Live record:** [`../../.gcc/DEPENDENCY_REGISTRY.md`](../../.gcc/DEPENDENCY_REGISTRY.md) (the authoritative list). This document is the **policy**; the registry is the **record**.
> **Enforces:** AP-6 (reproducibility), AP-7 (boundaries), Rules **NR-2, NR-5, NR-8**

Defines how dependencies — **internal module edges, external libraries, and
tooling** — are classified, approved, audited, retired, upgraded, risk-assessed,
and traced. **Silent dependency changes are a named AI failure mode** (AI_Governance
§5.6); this policy is the defense.

> **Premise:** every dependency is a liability and a supply-chain attack surface. A
> dependency that is not **pinned, approved, recorded, and justified** does not
> belong in the repository (AP-6, NR-2/NR-5).

---

## 1. Dependency Classification
| Class | What | Governed by |
|-------|------|-------------|
| **Internal (module edge)** | An import between modules. | The acyclic graph; **only allowed edges** ([`../architecture/DEPENDENCY_GRAPH.md`](../architecture/DEPENDENCY_GRAPH.md), NR-8) |
| **External (runtime)** | A third-party library shipped in a module's runtime path. | Pinned + ADR + registry; reproducibility (AP-6) |
| **External (dev/test)** | A library used only in dev/CI/tests. | Pinned; lower blast radius but still recorded |
| **Tooling** | CI, version managers, containers, linters. | [`TOOLCHAIN_STANDARD.md`](./TOOLCHAIN_STANDARD.md) + registry §4 |
| **Future** | Anticipated but not committed (e.g. federated training). | FUTURE-scope promotion (RFC→ADR), Scope F-items |

## 2. Dependency Approval
Adding/changing any **external or tooling** dependency, or any **new module edge**,
is an **A2+ change**:
1. **Justify** — why it's needed; what it replaces; lighter alternatives considered.
2. **RFC → ADR** ([`../governance/RFC_Process.md`](../governance/RFC_Process.md), [`../governance/Decision_Governance.md`](../governance/Decision_Governance.md)).
3. **Pin** the exact version (lockfile); no "latest" (AP-6).
4. **Record** in [`../../.gcc/DEPENDENCY_REGISTRY.md`](../../.gcc/DEPENDENCY_REGISTRY.md) (same change set).
5. **Review** (Founder for A2+); **never** AI self-approval (NR-7).
A **new internal edge** additionally requires the Architecture Gate (G1) and may
not create a cycle or a forbidden edge (NR-8).

## 3. Dependency Audits
- **Per change:** the `architecture` workflow reconciles real edges against the
  registry; an **unrecorded edge is drift** (stop-and-remediate).
- **Per version gate / quarterly / post-dormancy:** full audit — every external/
  tooling dependency is pinned, justified, ADR-linked, and still needed; security
  posture reviewed (SEC risks).
- Findings are handled per [`../quality/FAILURE_HANDLING.md`](../quality/FAILURE_HANDLING.md).

## 4. Dependency Retirement
- A dependency no longer needed is **removed via an A2+ change** (ADR), its registry
  entry **marked retired** (kept, linked — append-only per [`../context/MEMORY_RETENTION_POLICY.md`](../context/MEMORY_RETENTION_POLICY.md)).
- Removing an internal edge updates the graph + affected READMEs in the same change.

## 5. Dependency Upgrades
- Upgrades are **scheduled, reviewed, lock-pinned, and CI-validated** before merge;
  never auto-merged.
- An upgrade that breaks an invariant test or reproducibility is **blocked**.
- **Security upgrades are prioritized** and tracked as **SEC** risks.
- Each upgrade is recorded (changelog + registry; ADR if it changes a contract).

## 6. Dependency Risk Assessment
Before approval, assess (feeds [`../governance/Risk_Governance.md`](../governance/Risk_Governance.md)):
- **Maintenance/health** (active? maintained?), **license** (compatible?),
  **security** (known CVEs? supply-chain trust?), **blast radius** (how many modules
  depend on it?), **reproducibility** (deterministic? pinnable?), **lock-in** (does it
  force vendor/hardware lock-in? — Scope R7, reject if so).
High-risk dependencies are registered as risks with mitigation.

## 7. Dependency Traceability
Every dependency links **both ways**: registry entry ↔ its ADR ↔ the change that
introduced it ↔ any risk it carries. This makes "why is this here / what relies on
it?" answerable deterministically (context recovery; [`../context/REPOSITORY_KNOWLEDGE_MODEL.md`](../context/REPOSITORY_KNOWLEDGE_MODEL.md)).

## 8. Current State (V0)
**No application dependencies** (no code). Tooling dependencies: Git, GitHub Actions
CI, shell/text tooling (registry §4). The full external-dependency categories are
**reserved** and activate at V1 (each via ADR). This is correct for V0, not a gap.

Changes to this document are governance-class and require an ADR.
