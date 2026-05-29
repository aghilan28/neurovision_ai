# VERSION STATUS

> **Document type:** AI Operating System (V0-P4) · **Tier 3 (live)**
> **Status:** Living — updated at each phase/version gate.
> **Owner:** Founder · **Kept current by:** the active contributor
> **Update procedure:** Update completion %, readiness, and exit-criteria checkboxes at each gate; record gate decisions as ADRs ([`DECISION_REGISTRY.md`](./DECISION_REGISTRY.md)). Log changes ([`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md)).
> **Last updated:** V0-P6
> **Canonical version definitions:** [`../docs/VERSION_EVOLUTION_MODEL.md`](../docs/VERSION_EVOLUTION_MODEL.md)

Tracks every version's status, completion, dependencies, readiness, risks, and
exit criteria. Completion % is a **rough maturity signal**, not a precise metric.
**No version may claim exit criteria until all prior versions have (NR-12).**

---

## Snapshot

| Version | Status | Completion | Depends on | Readiness for next |
|---------|--------|-----------:|------------|--------------------|
| **V0** Repository Foundation | 🟢 In progress (P6) | ~99% | — | Pending V0 gate |
| **V1** Offline EEG Platform | ⚪ Not started | 0% | V0 exit | — |
| **V2** Clinical Workflow | ⚪ Not started | 0% | V1 exit | — |
| **V3** Near Real-Time | ⚪ Not started | 0% | V2 exit | — |
| **V4** Hospital-Ready | ⚪ Not started | 0% | V3 exit | — |

Legend: 🟢 active · 🟡 at risk · ✅ complete · ⚪ not started.

---

## V0 — Repository Foundation
- **Status:** In progress (P1–P5 ✅; P6 completing). **Completion:** ~99%.
- **Dependencies:** none (root).
- **Risks:** RISK-0003 (arch drift pre-automation), RISK-0004 (doc entropy).
- **Exit criteria** ([`../docs/VERSION_EVOLUTION_MODEL.md`](../docs/VERSION_EVOLUTION_MODEL.md) §1):
  - [x] Constitution complete & internally consistent (P1).
  - [x] Architecture foundation complete; graph acyclic; import rules explicit (P2).
  - [x] Governance framework established (P3).
  - [x] AI operating system established (P4).
  - [x] Quality Assurance Foundation established (P5).
  - [x] Context Preservation System established (P6).
  - [ ] No undefined terms / no architectural contradictions — **verify at gate**.
  - [ ] V0-completion ADR recorded.
- **Readiness for V1:** **not yet** — pending the gate checks above.

## V1 — Offline EEG Platform
- **Status:** Not started. **Completion:** 0%.
- **Dependencies:** V0 exit criteria (NR-12).
- **Risks (anticipated):** preprocessing determinism (TECH/REPRO); leakage in split
  design (CLIN/ARCH); AI hallucination during first real code (AI).
- **Exit criteria** (§2 of the version model):
  - [ ] Preprocessing deterministic & versioned.
  - [ ] All metrics patient-disjoint; zero leakage.
  - [ ] Uncertainty calibrated; coverage measured.
  - [ ] Every result reproducible.
  - [ ] No principle/boundary violated.
- **Readiness:** blocked on V0 gate.

## V2 — Clinical Workflow Platform
- **Status:** Not started. **Completion:** 0%.
- **Dependencies:** V1 exit criteria.
- **Exit criteria:** end-to-end audit trail; uncertainty preserved/faithfully shown;
  frontend↔backend API-only; no V1 regression.

## V3 — Near Real-Time Platform
- **Status:** Not started. **Completion:** 0%.
- **Dependencies:** V2 exit criteria.
- **Exit criteria:** streaming preserves disjointness/determinism; latency/reliability
  met; drift detected; no V1/V2 regression.

## V4 — Hospital-Ready Foundation
- **Status:** Not started. **Completion:** 0%.
- **Dependencies:** V3 exit criteria.
- **Exit criteria:** deployable in hospital constraints; every output auditable;
  reliability under shift/load; governance complete. *(Maturity state, not a
  regulatory-clearance claim.)*

---

## Gate Procedure
At each version gate: run [`CHECKLISTS/version_gate_checklist.md`](./CHECKLISTS/version_gate_checklist.md),
verify all prior-version exit criteria remain satisfied (no regression of
cross-version invariants), record a **version-gate ADR**, and update this file.
