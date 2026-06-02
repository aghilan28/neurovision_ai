# `docs/environment/` — Development Environment Foundation Index (V0-P7)

> **Document type:** Development Environment Foundation (V0-P7) index · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Environment Owner role)
> **Update procedure:** Index updated (Documentation change) when an environment doc is added/renamed; policy changes are governance-class (ADR).
> **Parent:** [`../README.md`](../README.md) · **Workflows:** [`../../.github/workflows/`](../../.github/workflows/)

The **permanent engineering environment** — reproducible, deterministic,
AI-assisted, and forward-compatible to V1→V4 without redesign. This phase creates
**infrastructure** (standards, toolchain, workflows, bootstrap), not application
features. These are **Tier 2 (process authority)** documents; the CI **mechanizes**
the quality gates ([`../quality/QUALITY_GATES.md`](../quality/QUALITY_GATES.md)).

---

## Documents

| Document | Defines |
|----------|---------|
| [`ENVIRONMENT_PHILOSOPHY.md`](./ENVIRONMENT_PHILOSOPHY.md) | What the environment guarantees; core principles; where `.github/` fits. |
| [`DEVELOPMENT_STANDARDS.md`](./DEVELOPMENT_STANDARDS.md) | Coding/repo/naming/testing/docs/AI/review/release standards + examples + anti-patterns. |
| [`TOOLCHAIN_STANDARD.md`](./TOOLCHAIN_STANDARD.md) | Required/optional/approved/forbidden tools; version/update/compat; AI + MCP standards. |
| [`LOCAL_DEVELOPMENT.md`](./LOCAL_DEVELOPMENT.md) | Fresh-machine setup → startup → troubleshooting → recovery → validation. |
| [`GIT_WORKFLOW.md`](./GIT_WORKFLOW.md) | Feature/architecture/research/hotfix/release workflows; naming; merge/Lore/governance/approval. |
| [`BRANCH_PROTECTION_POLICY.md`](./BRANCH_PROTECTION_POLICY.md) | Protected branches; merge restrictions; required checks; reviews; emergency. |
| [`DEPENDENCY_MANAGEMENT.md`](./DEPENDENCY_MANAGEMENT.md) | Classification/approval/audit/retirement/upgrade/risk/traceability. |
| [`SECRETS_MANAGEMENT.md`](./SECRETS_MANAGEMENT.md) | Categories/storage/rotation/access/audit/recovery/incident/future-production. |
| [`CI_CD_ARCHITECTURE.md`](./CI_CD_ARCHITECTURE.md) | CI flows + stages + diagrams; maps workflows → gates → validation. |
| [`ENVIRONMENT_VALIDATION.md`](./ENVIRONMENT_VALIDATION.md) | Environment validation gates EV-1…EV-6. |
| [`REPOSITORY_BOOTSTRAP.md`](./REPOSITORY_BOOTSTRAP.md) | The deterministic clone→work startup. |
| [`ONBOARDING_WORKFLOW.md`](./ONBOARDING_WORKFLOW.md) | Developer/AI/architecture/governance/context/quality onboarding + checkpoints. |

## CI/CD workflows (the automated arm)
[`../../.github/workflows/`](../../.github/workflows/): `documentation.yml` (G2),
`architecture.yml` (G1), `governance.yml` (G8), `context.yml` (G7), `quality.yml`
(G4/G5, [V1+] test stages), `repository-health.yml` (aggregate/RQI, scheduled).

## How the environment fits together
```
            ENVIRONMENT_PHILOSOPHY  (reproducible/deterministic/forward-compatible)
                       │
   ┌──────────┬────────┼─────────┬───────────────┬───────────────┐
   ▼          ▼        ▼         ▼               ▼               ▼
 DEVELOPMENT TOOLCHAIN DEPENDENCY SECRETS    GIT_WORKFLOW   BRANCH_PROTECTION
 STANDARDS   STANDARD  MANAGEMENT MANAGEMENT      │               │
   └──────────┴────────┴─────────┴───────────────┴───────────────┘
                       │ enforced by
              CI_CD_ARCHITECTURE  ──►  .github/workflows/*  (mechanizes gates G1–G8)
                       │ validated by
              ENVIRONMENT_VALIDATION (EV-1..EV-6)
                       │ entered via
          REPOSITORY_BOOTSTRAP  ──►  ONBOARDING_WORKFLOW (+ .gcc recovery/onboarding)
```

## Reading order (first time)
1. [`ENVIRONMENT_PHILOSOPHY.md`](./ENVIRONMENT_PHILOSOPHY.md)
2. [`REPOSITORY_BOOTSTRAP.md`](./REPOSITORY_BOOTSTRAP.md) → [`ONBOARDING_WORKFLOW.md`](./ONBOARDING_WORKFLOW.md) → [`LOCAL_DEVELOPMENT.md`](./LOCAL_DEVELOPMENT.md)
3. [`GIT_WORKFLOW.md`](./GIT_WORKFLOW.md), [`BRANCH_PROTECTION_POLICY.md`](./BRANCH_PROTECTION_POLICY.md)
4. [`TOOLCHAIN_STANDARD.md`](./TOOLCHAIN_STANDARD.md), [`DEPENDENCY_MANAGEMENT.md`](./DEPENDENCY_MANAGEMENT.md), [`SECRETS_MANAGEMENT.md`](./SECRETS_MANAGEMENT.md)
5. [`CI_CD_ARCHITECTURE.md`](./CI_CD_ARCHITECTURE.md), [`ENVIRONMENT_VALIDATION.md`](./ENVIRONMENT_VALIDATION.md), [`DEVELOPMENT_STANDARDS.md`](./DEVELOPMENT_STANDARDS.md)

All changes to documents in this directory are **governance-class** and require an
ADR ([`../governance/Decision_Governance.md`](../governance/Decision_Governance.md)).
