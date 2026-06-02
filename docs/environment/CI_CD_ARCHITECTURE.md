# CI/CD ARCHITECTURE

> **Document type:** Development Environment Foundation (V0-P7) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Environment Owner role)
> **Update procedure:** Governance-class change (ADR); workflow changes are governance/tooling changes.
> **Mechanizes:** the quality gates ([`../quality/QUALITY_GATES.md`](../quality/QUALITY_GATES.md) G1–G8), the audits ([`../quality/`](../quality/), [`../context/CONTEXT_AUDIT_SYSTEM.md`](../context/CONTEXT_AUDIT_SYSTEM.md)), and Principle **AP-11** (governance by construction)
> **Workflows:** [`../../.github/workflows/`](../../.github/workflows/)

This is the design of the CI/CD system — the **automated arm** of governance and
quality. CI is where the rules stop being aspirational and start being **enforced
on every PR** (AP-11). The pipeline is built so future **testing**, **deployment**,
and **release** flows slot in without redesign.

> **Premise:** *machines check mechanics; humans review meaning.* CI runs the
> objective checks first so human review can focus on judgment. A red pipeline
> blocks merge — always.

---

## 1. CI Flow (overview)

```
 PR opened/updated ─► [parallel automated workflows] ─► all green? ─► human review ─► merge to main
        │                     │                                              │
        │   ┌─────────────────┼───────────────────────────┐                 │ (Branch Protection)
        ▼   ▼                 ▼                ▼            ▼                 ▼
   documentation       architecture      governance     context        quality [V1+]
      (G2)                (G1)              (G8)          (G7)          (G4/G5)
        └──────────────── any failure ⇒ PR blocked (stop-and-remediate) ──────┘

 scheduled (cron) + manual ─► repository-health ─► RQI + audits summary ─► findings → risks/defects
```

## 2. Workflows → Gates → Validation map

| Workflow | Gate(s) | Validation category | Runs |
|----------|---------|---------------------|------|
| [`documentation.yml`](../../.github/workflows/documentation.yml) | **G2** | VC-DOC / VC-REPO | PR + push |
| [`architecture.yml`](../../.github/workflows/architecture.yml) | **G1** | VC-ARCH | PR + push |
| [`governance.yml`](../../.github/workflows/governance.yml) | **G8** | (decision/ADR/change-class) | PR + push |
| [`context.yml`](../../.github/workflows/context.yml) | **G7** | (CA-1…CA-7) | PR + push |
| [`quality.yml`](../../.github/workflows/quality.yml) | **G4/G5** (+ aggregate) | VC-TEST / VC-CLIN | PR + push (test stages **[V1+]**) |
| [`repository-health.yml`](../../.github/workflows/repository-health.yml) | aggregate / RQI | all | schedule + manual |

(Gate definitions: [`../quality/QUALITY_GATES.md`](../quality/QUALITY_GATES.md). Metrics
the health job reports: [`../quality/QUALITY_METRICS.md`](../quality/QUALITY_METRICS.md) M1–M12 + RQI.)

## 3. Stage Definitions

### 3.1 Validation Flow (active in V0 — docs/structure)
1. **Structure** — every required directory has a governance README (VC-REPO).
2. **Documentation** — broken-link scan; placeholder scan; Owner/Update-procedure
   presence; Glossary-term presence (G2 / VC-DOC).
3. **Architecture** — required architecture docs present; **no stray AP/NR IDs**;
   import-rule matrix present + acyclic ordering asserted; **[V1+]** real-import scan
   vs. the allowed graph (G1 / VC-ARCH).
4. **Governance** — governance doc set present; PR change-class/ADR convention
   checks; no governance contradiction signals (G8).
5. **Context** — registries present + carry "Last updated"; decisions index present;
   assumptions have verification plans; no undocumented-decision signal (G7 / CA-*).

### 3.2 Documentation Flow
The `documentation` workflow is the canonical doc gate (the six scans of
[`../quality/DOCUMENTATION_VALIDATION.md`](../quality/DOCUMENTATION_VALIDATION.md) §2),
runnable now and on every PR.

### 3.3 Governance Flow
`governance` verifies the change went through the right path (change classified;
ADR referenced when A2+; approver ≠ producing agent is enforced by branch
protection + review, not CI).

### 3.4 Context Validation Flow
`context` runs the context audits (CA-1…CA-7) at the lightweight, mechanizable
level: registries fresh, decisions/assumptions recorded, no orphaned memory
artifact, no obviously stale state file.

### 3.5 Future Testing Flow **[V1+]**
`quality` gains stages as code lands: install `--frozen`; run unit/integration/
contract/architecture tests; assert **invariant coverage = 100%**; patient-disjoint
+ determinism + calibration/coverage checks (Testing/Quality governance). Guarded by
the presence of code so it is inert (not failing) in V0.

### 3.6 Future Deployment Flow **[V3+]**
A `deploy` workflow (added at V3) builds the reproducible image, runs the full
regression + reliability/load + drift checks, and (V4) performs gated hospital
deployment with observability + tested rollback. **Reserved**, not built in V0.

### 3.7 Future Release Flow **[V0→V4]**
A `release` workflow performs release certification gating
([`../quality/RELEASE_CERTIFICATION.md`](../quality/RELEASE_CERTIFICATION.md)),
produces an immutable tag, and links changelog + ADRs.

## 4. Approval Requirements (CI ↔ humans)
- CI is a **required status check**: green CI is **necessary but not sufficient** —
  a human must still approve (NR-7).
- Branch protection ([`BRANCH_PROTECTION_POLICY.md`](./BRANCH_PROTECTION_POLICY.md))
  enforces: PR-only, required workflows green, ≥1 human approval, Founder for A3.
- CI **never** auto-approves or auto-merges; it gates, it does not decide.

## 5. Failure Actions
- Any required workflow red ⇒ **PR blocked** (stop-and-remediate); the failing check
  names the rule it enforces.
- A workflow that itself is broken is fixed as a tooling defect (a `chore`).
- A check that should have caught an escaped defect is **strengthened** after a
  postmortem (preventive quality).

## 6. Determinism & Parity
- CI runs the **same checks** a developer runs locally ([`LOCAL_DEVELOPMENT.md`](./LOCAL_DEVELOPMENT.md) §4)
  — local/CI parity (AP-3). **[V1+]** CI uses the **pinned** toolchain + lockfile.

## 7. Where CI Sits In the Architecture
`.github/` is **tooling infrastructure**, outside the production dependency graph and
**never imported by** any module (NR-8) — like `.gcc/`, `tools/`, `scripts/`. It
**observes and enforces**; it contains no domain logic.

## 8. Relationship To Other Documents
- Gates/metrics: [`../quality/QUALITY_GATES.md`](../quality/QUALITY_GATES.md), [`../quality/QUALITY_METRICS.md`](../quality/QUALITY_METRICS.md)
- Branch protection/validation: [`BRANCH_PROTECTION_POLICY.md`](./BRANCH_PROTECTION_POLICY.md), [`ENVIRONMENT_VALIDATION.md`](./ENVIRONMENT_VALIDATION.md)
- Workflows: [`../../.github/workflows/`](../../.github/workflows/)

Changes to this document are governance-class and require an ADR.
