# ARCHITECTURE GOVERNANCE

> **Document type:** Governance Layer (V0-P3)
> **Status:** Authoritative
> **Owner:** Founder (Architecture Owner role)
> **Update procedure:** Changes to this document are **governance-class changes** — they require an ADR (see [`Decision_Governance.md`](./Decision_Governance.md)) and follow [`Change_Management.md`](./Change_Management.md) → *Governance change* path.
> **Enforces:** Principles **AP-1, AP-7, AP-9, AP-11** and Rules **NR-5, NR-6, NR-8** ([`../ARCHITECTURAL_PRINCIPLES.md`](../ARCHITECTURAL_PRINCIPLES.md), [`../NON_NEGOTIABLE_RULES.md`](../NON_NEGOTIABLE_RULES.md))
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

This document governs **how the architecture of NeuroVision AI is allowed to
change.** The architecture defined in V0-P2 is authoritative; this document does
not redefine it — it defines the **process, roles, criteria, and safeguards** that
keep the architecture intact and intentionally evolved across V0 → V4.

The cardinal premise: **architecture is the most expensive thing to get wrong**
(Principle **AP-12**). Therefore architecture changes are the most heavily
governed class of change in the project.

---

## 1. What "Architecture" Means Here

**Architecture** is the set of structural decisions that are *expensive to
reverse* and that *many other decisions depend on.* In NeuroVision AI,
architecture is the realization of the constitution in structure:

- the **seven layers** (Presentation, Application, ML, DSP, Infrastructure,
  Governance, Context — [`../architecture/LAYERED_ARCHITECTURE.md`](../architecture/LAYERED_ARCHITECTURE.md));
- the **module set and their boundaries** ([`../architecture/MODULE_BOUNDARIES.md`](../architecture/MODULE_BOUNDARIES.md));
- the **dependency graph** and its acyclicity ([`../architecture/DEPENDENCY_GRAPH.md`](../architecture/DEPENDENCY_GRAPH.md));
- the **import rules** ([`../architecture/IMPORT_RULES.md`](../architecture/IMPORT_RULES.md));
- the **cross-version invariants** ([`../VERSION_EVOLUTION_MODEL.md`](../VERSION_EVOLUTION_MODEL.md) §6);
- the **system context and integration points** ([`../architecture/SYSTEM_CONTEXT.md`](../architecture/SYSTEM_CONTEXT.md)).

## 2. What Constitutes An Architecture Change

A change is **architecture-class** (and falls under this document) if it does any
of the following:

1. Adds, removes, renames, or re-scopes a **module** or **layer**.
2. Adds, removes, or redirects an **edge in the dependency graph** (any new
   import relationship between modules).
3. Alters a **module boundary** (its ownership, inputs, outputs, responsibilities,
   or forbidden actions).
4. Changes an **import rule** or the **acyclicity** property.
5. Touches a **cross-version invariant** (patient-disjoint validation, deterministic
   preprocessing, calibrated uncertainty, reproducibility, enforced boundaries,
   recorded decisions, no-rewrite, scope).
6. Changes a **public contract** between modules (e.g. the backend↔frontend API
   shape, the uncertainty/provenance payload).
7. Introduces a new **external dependency** that other modules will rely upon
   structurally (see [`Change_Management.md`](./Change_Management.md) and the
   Dependency Registry).
8. Changes an **integration point** or its constraints.

## 3. What Is *Not* Architecture

To prevent over-governance (which causes its own drift via avoidance), the
following are explicitly **not** architecture changes and are governed by the
lighter paths in [`Change_Management.md`](./Change_Management.md):

- Internal implementation of a module that **does not** alter its boundary,
  imports, or public contract.
- Bug fixes that restore intended behavior without changing structure.
- Adding tests, comments, or internal documentation.
- Performance tuning that preserves determinism, contracts, and boundaries.
- Editorial documentation changes that do not change meaning.

> **Rule of thumb:** if it changes *who depends on whom*, *what a module promises*,
> or *an invariant*, it is architecture. If it only changes *how a module fulfills
> an unchanged promise*, it is not.

---

## 4. Architecture Ownership

| Role | Held by (solo-founder context) | Responsibility |
|------|--------------------------------|----------------|
| **Architecture Owner** | **Founder** | Final authority on all architecture-class changes; only role that can approve them. |
| **Acting Architect** | Founder, or an AI agent operating under explicit founder supervision | Drafts proposals, performs impact analysis, ensures constitution alignment. |
| **Implementing Agent** | AI agent (Claude/Codex/Cursor/Kiro/MCP — see [`AI_Governance.md`](./AI_Governance.md)) | Implements an **approved** architecture change exactly as specified. |
| **Architecture Reviewer** | Founder (mandatory for architecture-class) | Reviews against the checklist in §12; can block. |
| **GCC (automated)** | The `.gcc/` layer + CI | Mechanically detects boundary/import/acyclicity violations (drift). |

In the solo-founder model, the Founder may hold several roles, **but the roles
remain distinct in the record**: an AI agent may *draft and implement*, but
**only the Founder approves** an architecture-class change. This separation is
what makes the audit trail meaningful (Principle **AP-8**).

---

## 5. How Architecture Changes Are Proposed

All architecture-class changes follow the **RFC → ADR** spine:

1. **Trigger** — a need is identified (new capability for a version, a discovered
   limitation, an integration point activation).
2. **RFC** — the proposer opens an RFC ([`RFC_Process.md`](./RFC_Process.md)) using
   the RFC template. The RFC must include: motivation, the precise structural
   change, impact on the dependency graph and invariants, alternatives, risks, and
   rollback plan.
3. **Impact analysis** — the Acting Architect maps every module, contract,
   invariant, and version affected (use the Architecture Impact Checklist,
   [`../../.gcc/CHECKLISTS/architecture_change_checklist.md`](../../.gcc/CHECKLISTS/architecture_change_checklist.md)).
4. **ADR** — the decision is recorded as an ADR ([`Decision_Governance.md`](./Decision_Governance.md))
   and indexed in the Decision Registry
   ([`../../.gcc/DECISION_REGISTRY.md`](../../.gcc/DECISION_REGISTRY.md)).
5. **Implementation** — only after approval; the change references the ADR.

No architecture-class change may be implemented before its ADR is **approved and
recorded** (Rule **NR-5**).

## 6. How Architecture Changes Are Approved

A proposed architecture change is **approved** only when **all** approval criteria
below are satisfied and the Architecture Owner records approval in the ADR.

### 6.1 Approval Criteria
- [ ] **Constitution-aligned:** does not violate any principle (AP-1…AP-12) or rule
  (NR-1…NR-15); does not weaken any cross-version invariant.
- [ ] **Acyclicity preserved:** the dependency graph remains a DAG.
- [ ] **No rewrite:** the change *extends* the architecture; it does not restart it
  (Rule **NR-6**). A change framed as "start over" is rejected outright.
- [ ] **Scope-valid:** the change serves an in-scope capability owned by the
  current or a planned version ([`../PROJECT_SCOPE.md`](../PROJECT_SCOPE.md), Rule **NR-13**).
- [ ] **Version-gate-valid:** it does not require a later version's capability before
  its prerequisites are met (Rule **NR-12**).
- [ ] **Impact understood:** every affected module/contract/invariant/version is
  enumerated.
- [ ] **Rollback defined:** a concrete rollback exists (see §11).
- [ ] **Documentation updated:** affected architecture docs and per-directory READMEs
  are updated in the same change set.
- [ ] **Risk classified:** the change carries a risk classification (§13) and any
  introduced risk is registered ([`Risk_Governance.md`](./Risk_Governance.md)).

---

## 7. Architecture Review Workflow

```
 proposer ──RFC──► impact analysis ──► ADR draft ──► Architecture Review (Founder)
                                                          │
                              ┌──────────── reject ◄──────┤
                              │                           │ approve
                              ▼                           ▼
                       revise & resubmit          implement (Implementing Agent)
                                                          │
                                                          ▼
                                            GCC checks + tests + Review_Governance
                                                          │
                                              ┌── fail ───┤── pass ──► merge
                                              ▼           
                                        fix or rollback   
```

- Architecture review is **always performed by the Founder** and is **never
  delegated to an AI agent as the sole reviewer** (Rule **NR-7**).
- The review uses the checklist in §12.
- Merge is gated on: approved ADR + passing GCC checks + passing tests + completed
  review ([`Review_Governance.md`](./Review_Governance.md)).

## 8. Architecture Escalation Process

Escalation exists for disagreement, ambiguity, or discovered conflict.

| Situation | Escalation path |
|-----------|-----------------|
| Reviewer and proposer disagree | Escalate to **Architecture Owner (Founder)**; decision recorded in the ADR. |
| Proposed change appears to violate a principle/rule | **Stop.** Open a governance decision; the change cannot proceed until resolved. |
| Two documents/contracts conflict | Treat as a **consistency defect**; the constitution (`docs/`) governs; reconcile before proceeding. |
| Emergency (production-impacting, V3+) | Use the **Emergency change** path ([`Change_Management.md`](./Change_Management.md)) with a **mandatory retroactive ADR within 72 hours**. |
| AI agent is uncertain whether something is architecture | Default to **treating it as architecture** and escalate to the Founder. |

The escalation default is **conservative**: when in doubt, govern more, not less.

---

## 9. Architecture Drift Detection

**Architecture drift** is divergence of the implemented system from the documented
architecture ([`../GLOSSARY.md`](../GLOSSARY.md)). It is detected by layered defenses:

1. **GCC import/boundary checks (primary, mechanical):** the `.gcc/` layer encodes
   the import rules and acyclicity and **fails CI** on violation (Principle **AP-11**,
   Rule **NR-8**).
2. **Boundary tests (`tests/`):** executable assertions (e.g. "frontend imports no
   domain module").
3. **Dependency Registry reconciliation:** the actual imports are reconciled
   against [`../../.gcc/DEPENDENCY_REGISTRY.md`](../../.gcc/DEPENDENCY_REGISTRY.md);
   any unrecorded edge is drift.
4. **Periodic architecture audit (§10).**

Any detected drift is a **stop-and-remediate** event (it triggers the violation
handling in §10.3), not a backlog item.

## 10. Architecture Audit Process

### 10.1 Cadence
- **Continuous:** GCC checks on every change.
- **Per phase/version gate:** a full architecture audit is a prerequisite for
  claiming a version's exit criteria (Rule **NR-12**).
- **Scheduled:** at minimum once per active development quarter, and after any
  long dormancy before resuming work (ties into
  [`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md)).

### 10.2 Audit Steps
1. Reconcile the **actual** dependency graph against the documented one.
2. Verify acyclicity holds.
3. Verify each module's real imports match its README contract.
4. Verify cross-version invariants are intact.
5. Verify every architecture change since the last audit has an ADR.
6. Record the audit result (pass/fail + findings) in the changelog
   ([`../../.gcc/CHANGELOG_SYSTEM.md`](../../.gcc/CHANGELOG_SYSTEM.md)).

### 10.3 Violation Handling
On any violation: **(a)** halt the offending change; **(b)** record the violation
as a risk ([`Risk_Governance.md`](./Risk_Governance.md)); **(c)** remediate
(fix-forward if trivial and safe, else rollback per §11); **(d)** record an ADR if
the resolution changes any decision; **(e)** add/strengthen the check that should
have caught it.

---

## 11. Architecture Rollback Procedures

Every architecture change must be reversible. Rollback strategy by stage:

| Stage at which a problem is found | Rollback action |
|-----------------------------------|-----------------|
| Pre-merge (review/CI) | Reject/abandon the change set; no rollback needed. |
| Post-merge, pre-release | Revert the change set (git revert of the merge); restore prior architecture docs; record in changelog. |
| Post-release (V3+) | Follow [`Release_Governance.md`](./Release_Governance.md) rollback; re-deploy the last known-good release; open an incident. |
| Invariant breach discovered later | Treat as **critical**; halt dependent work; reconstruct via the Decision Registry and Lore; remediate before any new work. |

**Rollback requirements for every architecture change:**
- The ADR records the **exact rollback procedure** before approval.
- Architecture docs are version-controlled so the prior state is recoverable.
- The Dependency Registry's prior state is recoverable.
- A rollback is itself a recorded change (changelog + ADR amendment).

---

## 12. Architecture Review Checklist

Used by the Architecture Reviewer (Founder) for every architecture-class change.
(Canonical machine copy: [`../../.gcc/CHECKLISTS/architecture_change_checklist.md`](../../.gcc/CHECKLISTS/architecture_change_checklist.md).)

- [ ] Is this genuinely an architecture change (§2)? If unsure, treat as one.
- [ ] Is there an **approved ADR** and an RFC trail?
- [ ] Does it preserve the **DAG** (no cycles)?
- [ ] Does it **extend, not rewrite** (AP-1 / NR-6)?
- [ ] Does it respect **all import rules** (NR-8)?
- [ ] Does it preserve **every cross-version invariant**?
- [ ] Is it **in scope** and **version-gate valid** (NR-12, NR-13)?
- [ ] Are **all affected modules/contracts/docs** updated in the same change set?
- [ ] Is there a concrete, recorded **rollback**?
- [ ] Is the **risk classified** and any new risk **registered**?
- [ ] Are **uncertainty/provenance contracts** preserved where relevant (AP-4/AP-5)?
- [ ] Was any **AI-generated** portion reviewed to the AI standard (NR-7, [`AI_Governance.md`](./AI_Governance.md))?

A "no" or "unknown" on any item **blocks** the change.

---

## 13. Per-Change Governance Specification

Every architecture change record (the ADR) must specify these fields explicitly:

| Field | Definition |
|-------|------------|
| **Initiator** | Who proposed it (Founder or named AI agent). |
| **Reviewer** | Who reviews/approves — **Founder** for all architecture-class changes. |
| **Approval Criteria** | The §6.1 checklist, all satisfied. |
| **Validation Requirements** | GCC checks pass; boundary/acyclicity tests pass; affected-module tests pass; invariant tests pass. |
| **Rollback Requirements** | The concrete rollback procedure (§11), recorded before approval. |
| **Documentation Requirements** | Which architecture docs + READMEs + registries are updated in the same change set. |
| **Risk Classification** | One of the tiers below, with rationale. |

### 13.1 Architecture Risk Classification (canonical tiers)
This scheme is shared across the governance suite (referenced by
[`Change_Management.md`](./Change_Management.md), [`Review_Governance.md`](./Review_Governance.md),
[`Risk_Governance.md`](./Risk_Governance.md)).

| Tier | Name | Meaning | Approval | Review depth |
|------|------|---------|----------|--------------|
| **A0** | Editorial | No structural effect (docs/comments). | Implementing Agent | Light |
| **A1** | Minor | Internal change, no boundary/contract effect. | Reviewer | Standard |
| **A2** | Major | New contract or external dependency; no invariant effect. | Founder | Deep |
| **A3** | Architecture-critical | Touches layers, dependency edges, invariants, or import rules. | **Founder (mandatory)** | **Deepest + ADR** |
| **AE** | Emergency | Time-critical (V3+); follows emergency path. | Founder (retro ADR ≤72h) | Post-hoc deep |

Anything at **A2 or above** requires an ADR. **A3** additionally requires an RFC
and a full architecture audit before the version gate.

---

## 14. Architecture Violation Examples

Concrete, governed examples (each maps to a rule):

- `frontend/` importing `ml/` or `preprocessing/` → **NR-8** (forbidden import).
- `preprocessing/` importing any internal module → **NR-8 / NR-9** (breaks the
  deterministic leaf).
- Introducing `ml/ → evaluation/` → **NR-8** (creates a cycle).
- "Rewriting the module layout for a new framework" → **NR-6** (rewrite).
- Adding a backend↔frontend coupling via shared imported types instead of the API
  → **NR-8** (boundary breach).
- Shipping a model swap with no ADR → **NR-5** (undocumented architecture change).
- Building V3 streaming before V1/V2 gates are met → **NR-12** (version skip).
- Dropping the uncertainty field from the API payload "to simplify" → **NR-4**
  (and an architecture contract breach).

Each example is **stop-and-remediate** and must be caught by GCC, tests, or review.

---

## 15. Relationship To Other Governance Documents
- Decisions: [`Decision_Governance.md`](./Decision_Governance.md) · Proposals: [`RFC_Process.md`](./RFC_Process.md)
- Change paths: [`Change_Management.md`](./Change_Management.md) · Review: [`Review_Governance.md`](./Review_Governance.md)
- Risk: [`Risk_Governance.md`](./Risk_Governance.md) · AI: [`AI_Governance.md`](./AI_Governance.md)
- Mechanization & state: [`../../.gcc/README.md`](../../.gcc/README.md), [`../../.gcc/DEPENDENCY_REGISTRY.md`](../../.gcc/DEPENDENCY_REGISTRY.md)

Changes to this document are governance-class and require an ADR.
