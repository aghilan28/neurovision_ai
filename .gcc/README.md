# `.gcc/` — Governance & Context Control (GCC) Layer

> **Layer:** Governance Layer (cross-cutting over all other layers)
> **Directory README type:** Repository Architecture Foundation (V0-P2)
> **Status (V0):** **Contract defined here (V0-P2); mechanisms implemented in V0-P3.**
> **Governing docs:** AP-1/AP-7/AP-8/AP-9/AP-11 and **all** of [`../docs/NON_NEGOTIABLE_RULES.md`](../docs/NON_NEGOTIABLE_RULES.md)

**GCC = Governance & Context Control.** This is the layer that makes governance
**mechanical instead of aspirational** (Principle **AP-11**). It encodes the
project's boundaries, import rules, decision records, and context controls in a
**machine-checkable** form, so that **architecture drift** and **context drift**
are *detected*, not discovered after the damage is done.

> GCC is *defined* in Phase **V0-P2** (this contract) and *implemented* in Phase
> **V0-P3 (Governance Layer)** — the immediate next phase after this foundation.

---

## Purpose
Mechanize the constitution: enforce module boundaries and import rules, manage
**decision records**, maintain audit trails, and operate the **Lore Protocol** so
the repository's intent survives team and AI-agent turnover.

## Responsibilities
- **Boundary & import enforcement:** encode the rules in
  [`../docs/architecture/IMPORT_RULES.md`](../docs/architecture/IMPORT_RULES.md)
  and [`../docs/architecture/DEPENDENCY_GRAPH.md`](../docs/architecture/DEPENDENCY_GRAPH.md)
  as checks that **fail the build** on violation (AP-7, NR-8).
- **Decision records:** store consequential, versioned, dated decisions with
  rationale and alternatives (AP-9, NR-5).
- **Drift detection:** detect divergence of implementation from documented
  architecture (architecture drift) and loss of rationale (context drift).
- **Technical-debt registry:** record debt with risk + repayment plan; enforce the
  per-version debt budget (NR-2).
- **Version gates:** record satisfaction of each version's exit criteria and
  enforce the no-skip rule (NR-12).
- **Lore Protocol:** maintain the durable context that keeps the repository
  self-explanatory (NR-14).

## Allowed dependencies
- ✅ Read access to **all** documents and modules (it inspects the whole repo).
- ✅ Tooling utilities from `tools/` and pinned third-party check/CI libraries.

## Forbidden dependencies
- ❌ Being imported **by** any production module — governance observes and
  constrains the platform; it is not part of the application's runtime graph (NR-8).
- ❌ Containing domain logic (DSP/ML/data/serving) — that belongs in the domain
  modules.

## Future responsibilities
- **V0-P3:** implement the GCC mechanisms (import checks, decision-record store,
  debt registry, version gates) and wire them into CI.
- **V1+:** enforce patient-disjoint/determinism/uncertainty contracts at the
  boundary (complementing `tests/`).
- **V2+:** verify end-to-end traceability/audit completeness (AP-8, NR-11).
- **V4:** provide the complete governance + audit substrate for hospital readiness.

## Version ownership
- **Owned by V0 (formally implemented in V0-P3); operated continuously V0 → V4.**
- Contract defined in **V0-P2** (this README).

## Examples
- A CI check that fails if `frontend/` imports any domain module (NR-8).
- A decision record capturing *why* a model family was chosen, with alternatives (NR-5).
- A debt-registry entry: "shortcut X taken, risk Y, repay by version Z" (NR-2).
- A version-gate record asserting V1 exit criteria are met before V2 work begins (NR-12).

## Boundary rules
- GCC is **cross-cutting**: it governs every layer but is **not imported by** any
  of them (see [`../docs/architecture/LAYERED_ARCHITECTURE.md`](../docs/architecture/LAYERED_ARCHITECTURE.md)).
- GCC is **authoritative for enforcement**, but the **constitution documents in
  `docs/` remain the source of truth**; GCC mechanizes them, it does not redefine
  them. A conflict between a GCC check and a `docs/` rule is a defect to reconcile,
  with the `docs/` rule governing intent.
- Changes to governance mechanisms are themselves **governance events** requiring a
  recorded decision (NR-5).

---

### Why this directory is hidden (`.gcc`)
The leading dot marks GCC as **infrastructure/governance**, distinct from the
product modules. It is always present, always authoritative, and intentionally set
apart from the application's own directory tree — a constant, cross-cutting
guardian rather than a feature module.
