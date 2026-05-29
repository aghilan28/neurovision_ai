# ENVIRONMENT PHILOSOPHY

> **Document type:** Development Environment Foundation (V0-P7) · **Tier 2 (process authority)**
> **Status:** Authoritative
> **Owner:** Founder (Environment Owner role)
> **Update procedure:** Governance-class change (ADR — [`../governance/Decision_Governance.md`](../governance/Decision_Governance.md)).
> **Enforces:** Principles **AP-3, AP-6, AP-7, AP-11, AP-12**; Rules **NR-8, NR-9, NR-10**
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

This is the root of the **Development Environment Foundation** (`docs/environment/`).
It defines the **permanent engineering environment** — the reproducible, deterministic,
AI-assisted, and forward-compatible operating context in which all of V1 → V4 is
built. P7 creates **infrastructure**, not application features.

> **Premise:** the environment is part of the platform's correctness. A
> non-reproducible environment produces non-reproducible results (NR-10); an
> ungoverned environment lets drift and entropy in through the back door. The
> environment must be **reproducible by construction** and **governed like code.**

---

## 1. What the Environment Must Guarantee

| Guarantee | Why | Realized by |
|-----------|-----|-------------|
| **Reproducibility** | A result/build must regenerate from pinned inputs (NR-10, AP-6). | Pinned toolchain + lockfiles + containers ([`TOOLCHAIN_STANDARD.md`](./TOOLCHAIN_STANDARD.md), [`DEPENDENCY_MANAGEMENT.md`](./DEPENDENCY_MANAGEMENT.md)) |
| **Determinism** | Same inputs ⇒ same outputs, every machine (AP-3). | Version pinning; no implicit/global state; CI parity ([`LOCAL_DEVELOPMENT.md`](./LOCAL_DEVELOPMENT.md)) |
| **AI-assisted development** | AI agents are first-class contributors. | Toolchain + onboarding + CI that enforce the AI governance ([`ONBOARDING_WORKFLOW.md`](./ONBOARDING_WORKFLOW.md)) |
| **Future ML workflows** | V1 brings models/evaluation. | Forward dependency + container strategy (no redesign) |
| **Future clinical workflows** | V2 brings the review workflow. | Backend/frontend strategy reserved; secrets/PII rules ([`SECRETS_MANAGEMENT.md`](./SECRETS_MANAGEMENT.md)) |
| **Future deployment workflows** | V3/V4 bring streaming + hospital deployment. | CI/CD architecture with reserved deploy stages ([`CI_CD_ARCHITECTURE.md`](./CI_CD_ARCHITECTURE.md)) |
| **Governance by construction** | Rules that are mechanized hold (AP-11). | CI workflows enforce the quality gates ([`.github/workflows/`](../../.github/workflows/)) |

## 2. Core Principles

1. **Reproducible or it didn't happen.** Every build/result derives from pinned,
   recorded inputs; an unpinned dependency is a defect (AP-6/NR-10).
2. **Deterministic across machines.** Local and CI must agree; "works on my
   machine" is a failure, not an excuse.
3. **Governed like code.** Environment changes follow [`../governance/Change_Management.md`](../governance/Change_Management.md)
   (new/changed dependency = **A2+**, ADR + Dependency Registry).
4. **Forward-compatible, never redesigned.** The environment is built so ML (V1),
   clinical (V2), real-time (V3), and deployment (V4) **slot in** without rewrite
   (AP-1).
5. **Infrastructure is outside the production graph.** `.github/`, `tools/`,
   `scripts/`, `.gcc/` are tooling/governance infrastructure — **never imported by
   production modules** (NR-8); they support the platform, they are not part of it.
6. **Secrets never enter the repository.** No credential is ever committed
   ([`SECRETS_MANAGEMENT.md`](./SECRETS_MANAGEMENT.md)); this is absolute.
7. **Bootstrap is deterministic.** A new human or AI agent can clone → initialize →
   validate → recover context → begin work **without asking questions**
   ([`REPOSITORY_BOOTSTRAP.md`](./REPOSITORY_BOOTSTRAP.md)).
8. **Mechanize the gates.** The quality gates (G1–G8, [`../quality/QUALITY_GATES.md`](../quality/QUALITY_GATES.md))
   are enforced by CI wherever automatable — this phase wires that enforcement.

## 3. Relationship To the Architecture (where `.github/` fits)

The environment introduces one new top-level infrastructure directory,
**`.github/`** (CI/CD workflows). It is **tooling infrastructure**, in the same
category as `.gcc/`, `tools/`, and `scripts/`:
- It is **cross-cutting** and **outside the production dependency graph**
  ([`../architecture/DEPENDENCY_GRAPH.md`](../architecture/DEPENDENCY_GRAPH.md)).
- It is **never imported by** any production module (NR-8).
- It **observes and enforces** the repository (like GCC); it does not contain domain
  logic.
This is consistent with the V0-P2 architecture and adds **no** new production
module or dependency edge (so it is **not** an architecture-class change to the
module graph; it is environment infrastructure).

## 4. What This Phase Is NOT
- **Not** application code (no preprocessing/ML/backend/frontend logic — that is V1+).
- **Not** a redesign of any prior phase — it *operationalizes* governance/quality
  (mechanizing the gates) and *adds* the engineering substrate.
- **Not** a place for secrets, vendor lock-in (Scope R7), or non-deterministic tooling.

## 5. The Environment Foundation (organization)
| Document | Defines |
|----------|---------|
| [`DEVELOPMENT_STANDARDS.md`](./DEVELOPMENT_STANDARDS.md) | Coding/repository/naming/testing/docs/AI/review/release standards + examples + anti-patterns. |
| [`TOOLCHAIN_STANDARD.md`](./TOOLCHAIN_STANDARD.md) | Required/optional/approved/forbidden tools; version/update/compat policies; AI/MCP standards. |
| [`LOCAL_DEVELOPMENT.md`](./LOCAL_DEVELOPMENT.md) | Fresh-machine setup → startup → troubleshooting → recovery → validation. |
| [`GIT_WORKFLOW.md`](./GIT_WORKFLOW.md) | Feature/architecture/research/hotfix/release workflows; naming; merge/Lore/governance/approval. |
| [`BRANCH_PROTECTION_POLICY.md`](./BRANCH_PROTECTION_POLICY.md) | Protected branches; merge restrictions; review/CI/approval; emergency. |
| [`DEPENDENCY_MANAGEMENT.md`](./DEPENDENCY_MANAGEMENT.md) | Classification/approval/audit/retirement/upgrade/risk/traceability. |
| [`SECRETS_MANAGEMENT.md`](./SECRETS_MANAGEMENT.md) | Categories/storage/rotation/access/audit/recovery/incident/future-production. |
| [`CI_CD_ARCHITECTURE.md`](./CI_CD_ARCHITECTURE.md) | CI flows, stages, diagrams, approval requirements; maps to the workflows. |
| [`ENVIRONMENT_VALIDATION.md`](./ENVIRONMENT_VALIDATION.md) | Environment validation gates + bootstrap/dependency/tool/CI/health/recovery validation. |
| [`REPOSITORY_BOOTSTRAP.md`](./REPOSITORY_BOOTSTRAP.md) | The deterministic clone→work startup process. |
| [`ONBOARDING_WORKFLOW.md`](./ONBOARDING_WORKFLOW.md) | Developer/AI/architecture/governance/context/quality onboarding + reading order + checkpoints. |

## 6. Relationship To Governance, Quality, Context
- **Governance:** environment changes are governed (Change_Management); CI enforces
  the gates (Review/Release governance).
- **Quality:** the workflows are the **automated arm** of the quality gates
  (G1–G8) and validation (VC-*); see [`CI_CD_ARCHITECTURE.md`](./CI_CD_ARCHITECTURE.md).
- **Context:** onboarding/bootstrap drive [`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md);
  environment dependencies are tracked in [`../../.gcc/DEPENDENCY_REGISTRY.md`](../../.gcc/DEPENDENCY_REGISTRY.md).

Changes to this document are governance-class and require an ADR.
