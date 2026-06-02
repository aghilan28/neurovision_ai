# Version Gate Checklist

> **Framework:** [`../VERSION_STATUS.md`](../VERSION_STATUS.md), [`../../docs/VERSION_EVOLUTION_MODEL.md`](../../docs/VERSION_EVOLUTION_MODEL.md), Rule **NR-12**
> Use when claiming a version's **exit criteria** (V0→V1, V1→V2, …). No version may
> claim exit criteria until **all prior versions** have. Record a **version-gate ADR**.

## Prerequisite (no-skip rule)
- [ ] **All prior versions' exit criteria** are satisfied and recorded (NR-12).
- [ ] No regression of any **cross-version invariant** (Version model §6).

## This version's exit criteria
- [ ] Every exit criterion for this version (from the version model) is **met and verified**.
- [ ] All this version's **required deliverables** exist and are complete.
- [ ] All this version's **required tests/validations** pass (Testing_Governance §3).

## Integrity audits (run at the gate)
- [ ] **Architecture audit** passed (Architecture_Governance §10): graph acyclic;
  real imports match contracts; Dependency Registry reconciled.
- [ ] **Documentation audit** passed (Documentation_Governance §8): no orphans/
  conflicts/staleness; all terms defined; links resolve; ownership present.
- [ ] **Lore audit** passed (LORE_PROTOCOL §9): every consequential change has a *why*.

## Risk & debt
- [ ] **No open Critical risk**; High risks have owners + mitigation
  ([`../ACTIVE_RISKS.md`](../ACTIVE_RISKS.md)).
- [ ] Technical-debt within this version's budget (V0 = **zero**); all debt recorded (NR-2).
- [ ] Open **assumptions** reviewed ([`../ACTIVE_ASSUMPTIONS.md`](../ACTIVE_ASSUMPTIONS.md)).

## Records
- [ ] **Version-gate ADR** recorded ([`../DECISION_REGISTRY.md`](../DECISION_REGISTRY.md)).
- [ ] [`../VERSION_STATUS.md`](../VERSION_STATUS.md), [`../CURRENT_STATE.md`](../CURRENT_STATE.md),
  [`../NEXT_STATE.md`](../NEXT_STATE.md) updated.
- [ ] **Changelog** entry for the gate.

## Decision
- [ ] **Founder** confirms the gate is passed and authorizes the next version.
