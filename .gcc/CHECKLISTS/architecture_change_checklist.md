# Architecture Change Checklist

> **Framework:** [`../../docs/governance/Architecture_Governance.md`](../../docs/governance/Architecture_Governance.md) §6/§12
> Use for any **architecture-class (A3)** change. A "no"/"unknown" on any item
> **blocks** the change. Reviewer for architecture changes is the **Founder**.

## Classification
- [ ] Confirmed this **is** an architecture change (Architecture_Governance §2). *(If unsure, treat as one.)*
- [ ] Risk classified as **A3** (or **AE** with retro-ADR plan).

## Proposal trail
- [ ] An **RFC** exists ([`../../docs/governance/RFC_Process.md`](../../docs/governance/RFC_Process.md)).
- [ ] An **ADR** is drafted with all mandatory fields ([`../TEMPLATES/ADR_TEMPLATE.md`](../TEMPLATES/ADR_TEMPLATE.md)).
- [ ] Impact analysis enumerates **every** affected module/contract/invariant/version.

## Constitution & invariants
- [ ] No principle (AP-1…AP-12) or rule (NR-1…NR-15) violated.
- [ ] **Extends, does not rewrite** the architecture (AP-1 / NR-6).
- [ ] Dependency graph remains **acyclic** (no cycle introduced).
- [ ] **All import rules** respected ([`../../docs/architecture/IMPORT_RULES.md`](../../docs/architecture/IMPORT_RULES.md)); no forbidden edge.
- [ ] **No cross-version invariant weakened** (patient-disjoint, determinism,
  uncertainty, reproducibility, boundaries, recorded decisions, no-rewrite, scope).
- [ ] Uncertainty/provenance contracts preserved where relevant (AP-4/AP-5).

## Scope & version
- [ ] **In scope** ([`../../docs/PROJECT_SCOPE.md`](../../docs/PROJECT_SCOPE.md), NR-13).
- [ ] **Version-gate valid** — no later-version capability required early (NR-12).

## Validation & safety net
- [ ] Boundary + **acyclicity** tests cover the change.
- [ ] Invariant tests cover the change.
- [ ] GCC checks pass (or are updated to catch the new rule).
- [ ] **Dependency Registry** updated for any edge/dependency change.

## Reversibility & records
- [ ] Concrete **rollback** recorded **before** approval (Architecture_Governance §11).
- [ ] All affected **docs/READMEs** updated in the same change set.
- [ ] Any introduced **risk** registered; any **debt** recorded (NR-2).
- [ ] Any **AI-generated** portion passed the AI-review checklist (NR-7).
- [ ] **Changelog** entry prepared.

## Approval
- [ ] **Founder** approval recorded in the ADR (producing agent did **not** self-approve, NR-7).
