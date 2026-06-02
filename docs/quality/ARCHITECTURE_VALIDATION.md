# ARCHITECTURE VALIDATION

> **Document type:** Quality Assurance Foundation (V0-P5) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Architecture Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Policy authority:** [`../governance/Architecture_Governance.md`](../governance/Architecture_Governance.md) (this document **operationalizes** its drift detection + audit; on conflict, Architecture Governance governs).
> **Feeds:** the **Architecture Gate (G1)** in [`QUALITY_GATES.md`](./QUALITY_GATES.md) and **VC-ARCH** in [`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md)

This document is the **architecture compliance framework**: the concrete checks
that prove the implemented system still matches the architecture defined in V0-P2.
It turns the principles AP-1/AP-7 and rules NR-6/NR-8 into **runnable validation**.

> **Premise:** architecture that is not continuously validated **drifts**. Drift is
> silent, compounding, and expensive. This framework makes drift loud and early.

---

## 1. What Is Validated

| # | Target | Source of truth | Check |
|---|--------|-----------------|-------|
| 1 | **Dependency rules** | [`../architecture/DEPENDENCY_GRAPH.md`](../architecture/DEPENDENCY_GRAPH.md) | Every actual import edge is an allowed edge; graph is **acyclic**. |
| 2 | **Import rules** | [`../architecture/IMPORT_RULES.md`](../architecture/IMPORT_RULES.md) | No forbidden import (e.g. `frontend`→domain; `preprocessing`→anything). |
| 3 | **Module boundaries** | [`../architecture/MODULE_BOUNDARIES.md`](../architecture/MODULE_BOUNDARIES.md) + per-dir READMEs | Each module's real imports/exports match its declared contract. |
| 4 | **Repository structure** | [`../architecture/LAYERED_ARCHITECTURE.md`](../architecture/LAYERED_ARCHITECTURE.md) | The 7-layer tree intact; every directory has a governance README + Owner. |
| 5 | **Version alignment** | [`../VERSION_EVOLUTION_MODEL.md`](../VERSION_EVOLUTION_MODEL.md) | No later-version capability built before its gate (NR-12); subsystem activation matches version. |
| 6 | **Architecture decisions** | [`../../.gcc/DECISION_REGISTRY.md`](../../.gcc/DECISION_REGISTRY.md) | Every architecture change has an approved ADR (NR-5). |

## 2. What Is Detected

| Defect | Definition | Detected by |
|--------|------------|-------------|
| **Architecture drift** | Implemented system diverges from documented architecture. | Graph reconciliation (§3.1); audit (§4). |
| **Unauthorized dependencies** | An import edge not in the allowed graph; an unrecorded external dependency. | Import scan (§3.1); Dependency Registry reconciliation. |
| **Boundary violations** | A module reaches outside its declared contract (e.g. `frontend` importing `ml`). | Import scan + boundary tests. |
| **Hidden coupling** | Modules coupled via shared mutable state, side channels, or "utility" back-doors instead of declared contracts. | Audit (§4) + review; `tools/`/`scripts/` must never be a production dependency. |
| **Cycle introduction** | Any directed cycle in the module graph. | Acyclicity check (topological sort). |
| **Rewrite attempt** | A change that restarts rather than extends the architecture. | Review (NR-6); architecture-change checklist. |

## 3. Validation Methods (layered defenses)

### 3.1 Mechanical (GCC + tests) — primary, every change
- **Import/edge scan:** enumerate each module's imports; assert each is an
  **allowed** edge; assert **no forbidden** edge (the 12×12 matrix in
  [`../architecture/IMPORT_RULES.md`](../architecture/IMPORT_RULES.md)).
- **Acyclicity:** topologically sort the module graph; any back-edge ⇒ fail.
- **Leaf check:** assert `preprocessing` imports nobody internal; `frontend`
  imports no domain module.
- **Support-isolation:** assert no production module imports `tests/`, `tools/`, or
  `scripts/`, and that domain modules do not code-import infra (`monitoring`/`deployment`).
- These run in CI (Architecture Gate G1) and **fail the build** on violation (AP-11/NR-8).

### 3.2 Dependency Registry reconciliation — every change touching deps
Compare actual imports + external dependencies against
[`../../.gcc/DEPENDENCY_REGISTRY.md`](../../.gcc/DEPENDENCY_REGISTRY.md). Any
**unrecorded** edge or dependency is drift → stop-and-remediate (and a new ADR if
the edge should be allowed).

### 3.3 Boundary tests (`tests/`) — executable assertions
Per [`TEST_STRATEGY.md`](./TEST_STRATEGY.md) §2.4 — complement (never replace) GCC.

### 3.4 Human architecture review — A3 changes
Founder uses [`../../.gcc/CHECKLISTS/architecture_change_checklist.md`](../../.gcc/CHECKLISTS/architecture_change_checklist.md);
catches **hidden coupling** and **rewrite** attempts that mechanical checks miss.

## 4. Architecture Audit Process

Operationalizes [`../governance/Architecture_Governance.md`](../governance/Architecture_Governance.md) §10.

**Cadence:** continuous (GCC per change) · full audit at **every version gate** ·
**quarterly** during active development · **after dormancy** before resuming
([`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md) §5).

**Steps (record the result in the changelog):**
1. Reconcile the **actual** dependency graph against the documented graph.
2. Verify **acyclicity** holds.
3. Verify each module's real imports match its README/boundary contract.
4. Verify **cross-version invariants** are intact (patient-disjoint, determinism,
   uncertainty, reproducibility, boundaries, recorded decisions, no-rewrite, scope).
5. Verify **every architecture change since the last audit has an ADR**.
6. Verify **version alignment** (no premature later-version capability; NR-12).
7. Verify **no hidden coupling** (no shared-state/utility back-doors; support code
   not a production dependency).
8. Record pass/fail + findings ([`../../.gcc/CHANGELOG_SYSTEM.md`](../../.gcc/CHANGELOG_SYSTEM.md)); open risks/postmortems for any finding.

**Audit evidence** (reproducible, recorded): the import scan output, the
topological-sort result, the registry reconciliation diff, and the invariant-test
results.

## 5. Failure Handling
On any violation (per Architecture_Governance §10.3):
1. **Halt** the offending change.
2. **Record** the violation as an **ARCH** risk ([`../governance/Risk_Governance.md`](../governance/Risk_Governance.md)).
3. **Remediate** — fix-forward if trivial and safe, else **rollback** (Architecture_Governance §11).
4. **Record an ADR** if the resolution changes a decision.
5. **Add/strengthen the check** that should have caught it (preventive quality).
6. If it reached `main`, write a **postmortem** ([`../context/POSTMORTEM_FRAMEWORK.md`](../context/POSTMORTEM_FRAMEWORK.md)).

## 6. Evidence → Gate → Metric
- **Gate:** Architecture Gate (G1).
- **Metric:** *Architecture Violations* + *Dependency Violations*
  ([`QUALITY_METRICS.md`](./QUALITY_METRICS.md)) — target **zero** open.

## 7. Relationship To Other Documents
- Policy: [`../governance/Architecture_Governance.md`](../governance/Architecture_Governance.md) · Graph/rules: [`../architecture/`](../architecture/)
- Gates/validation: [`QUALITY_GATES.md`](./QUALITY_GATES.md), [`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md) · Registry: [`../../.gcc/DEPENDENCY_REGISTRY.md`](../../.gcc/DEPENDENCY_REGISTRY.md)

Changes to this document are governance-class and require an ADR.
