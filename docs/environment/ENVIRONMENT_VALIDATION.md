# ENVIRONMENT VALIDATION

> **Document type:** Development Environment Foundation (V0-P7) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Environment Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Feeds:** the **Environment Readiness** assessment in [`../certification/V0_READINESS_ASSESSMENT.md`](../certification/V0_READINESS_ASSESSMENT.md)
> **Mechanized by:** [`../../.github/workflows/`](../../.github/workflows/)

Defines the **gates that prove the environment itself is correct** — reproducible,
deterministic, and able to bootstrap, validate, and recover. These are the
environment analogue of the quality gates: the environment is not "ready" until it
passes them.

> **Premise:** an unvalidated environment is an unreliable environment. Before we
> trust results from it (V1+), we validate the environment that produced them.

---

## 1. Environment Validation Gates (EV-*)

| Gate | Verifies | Pass criterion | Mechanized by |
|------|----------|----------------|---------------|
| **EV-1 Bootstrap** | A fresh clone reaches a working, validated state by the documented steps. | [`REPOSITORY_BOOTSTRAP.md`](./REPOSITORY_BOOTSTRAP.md) steps succeed with no undocumented action. | (manual + onboarding test) |
| **EV-2 Dependency** | All dependencies pinned, approved, recorded; no unrecorded edge. | `architecture` reconciliation green; registry matches reality. | `architecture.yml` |
| **EV-3 Tool** | Required tools present at pinned versions; local==CI parity. | Tool/version check passes; **[V1+]** lockfile install `--frozen` succeeds. | `quality.yml` **[V1+]**, manual (V0) |
| **EV-4 CI** | All required workflows run and are green on a PR. | `documentation` + `architecture` + `governance` + `context` green. | the workflows |
| **EV-5 Repository Health** | Structure/registries/freshness/RQI within thresholds. | `repository-health` summary green; no hard-zero metric breached. | `repository-health.yml` |
| **EV-6 Recovery** | Context recovery + post-dormancy audits succeed deterministically. | Recovery validation questions answered from the repo alone. | (manual + `context.yml`) |

## 2. Bootstrap Validation (EV-1)
Confirms a new developer/AI agent can **clone → initialize → validate → recover
context → begin work without asking questions** ([`REPOSITORY_BOOTSTRAP.md`](./REPOSITORY_BOOTSTRAP.md)).
Evidence: the bootstrap steps run clean; the onboarding validation checkpoints pass
([`ONBOARDING_WORKFLOW.md`](./ONBOARDING_WORKFLOW.md)).

## 3. Dependency Validation (EV-2)
- Every external/tooling dependency is **pinned + ADR-linked + in the registry**.
- The actual module-import graph reconciles against the allowed graph (no
  unrecorded/forbidden edge — NR-8). **V0:** no application deps ⇒ trivially clean.

## 4. Tool Validation (EV-3)
- Required tools present; versions match the pins (TOOLCHAIN_STANDARD §5/§7).
- **[V1+]:** `install --frozen` reproduces the exact dependency set; container build
  reproduces the toolchain.

## 5. CI Validation (EV-4)
- All **required** workflows are configured and green on the PR
  ([`BRANCH_PROTECTION_POLICY.md`](./BRANCH_PROTECTION_POLICY.md) §3).
- The workflows run the **same logic** as local checks (parity).

## 6. Repository Health Validation (EV-5)
- `repository-health` reports: structure (every dir has a README), registries carry
  "Last updated", no broken links, no placeholders, no stray AP/NR IDs, and the
  **RQI** + hard-zero metrics ([`../quality/QUALITY_METRICS.md`](../quality/QUALITY_METRICS.md) §2).
- Any hard-zero breach (architecture/dependency violations, undocumented decisions,
  context-integrity findings) **fails** EV-5.

## 7. Recovery Validation (EV-6)
- Run [`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md)
  and answer its §3 validation questions **from the repository alone**.
- After dormancy: documentation + architecture + context audits pass before resuming.

## 8. Cadence
- **Per PR:** EV-2, EV-4 (+ EV-3/EV-5 partial via the workflows).
- **On schedule + on demand:** EV-5 (repository-health).
- **At onboarding / post-dormancy:** EV-1, EV-6.
- **At the V0 certification + every version gate:** all EV gates
  ([`../certification/V0_AUDIT_FRAMEWORK.md`](../certification/V0_AUDIT_FRAMEWORK.md) Environment Audit).

## 9. Failure Handling
An EV failure is handled per [`../quality/FAILURE_HANDLING.md`](../quality/FAILURE_HANDLING.md)
(class **OPS** or **REPO**/**CTX** as applicable): contain (block), recover, record,
prevent (strengthen the check).

Changes to this document are governance-class and require an ADR.
