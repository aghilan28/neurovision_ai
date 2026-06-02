# VERSION STATUS

> **Document type:** AI Operating System (V0-P4) · **Tier 3 (live)**
> **Status:** Living — updated at each phase/version gate.
> **Owner:** Founder · **Kept current by:** the active contributor
> **Update procedure:** Update completion %, readiness, and exit-criteria checkboxes at each gate; record gate decisions as ADRs ([`DECISION_REGISTRY.md`](./DECISION_REGISTRY.md)). Log changes ([`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md)).
> **Last updated:** V0-P8 (V0 CERTIFIED WITH CONDITIONS — ADR-0001)
> **Canonical version definitions:** [`../docs/VERSION_EVOLUTION_MODEL.md`](../docs/VERSION_EVOLUTION_MODEL.md)

Tracks every version's status, completion, dependencies, readiness, risks, and
exit criteria. Completion % is a **rough maturity signal**, not a precise metric.
**No version may claim exit criteria until all prior versions have (NR-12).**

---

## Snapshot

| Version | Status | Completion | Depends on | Readiness for next |
|---------|--------|-----------:|------------|--------------------|
| **V0** Repository Foundation | ✅ **Complete (CERTIFIED WITH CONDITIONS)** | 100% | — | V1 authorized (gated) |
| **V1** Offline EEG Platform | 🟢 Eligible to begin | 0% | V0 exit ✅ | — |
| **V2** Clinical Workflow | ⚪ Not started | 0% | V1 exit | — |
| **V3** Near Real-Time | ⚪ Not started | 0% | V2 exit | — |
| **V4** Hospital-Ready | ⚪ Not started | 0% | V3 exit | — |

Legend: 🟢 active/eligible · 🟡 at risk · ✅ complete · ⚪ not started.

---

## V0 — Repository Foundation
- **Status:** ✅ **Complete — CERTIFIED WITH CONDITIONS** (ADR-0001, V0-P8).
  **Completion:** 100% (P1–P8 delivered).
- **Dependencies:** none (root).
- **Certification:** [`../docs/certification/V0_COMPLETION_REPORT.md`](../docs/certification/V0_COMPLETION_REPORT.md)
  — readiness ~94/100; 0 open Critical risks; 0 Blocker/Major gaps.
- **Open conditions (V1-entry, non-blocking):** observe CI green on first PR (ASM-0006);
  cold-onboarding test (ASM-0001); configure host branch protection.
- **Exit criteria** (all MET — [`../docs/certification/V0_EXIT_CRITERIA.md`](../docs/certification/V0_EXIT_CRITERIA.md)):
  - [x] Constitution (P1) · Architecture (P2) · Governance (P3) · AI OS (P4).
  - [x] Quality (P5) · Context (P6) · Environment + CI (P7) · Certification (P8).
  - [x] No undefined terms / no architectural contradictions (audited).
  - [x] V0-completion ADR recorded (ADR-0001).
- **Readiness for V1:** **authorized** under [`../docs/certification/V1_READINESS_GATE.md`](../docs/certification/V1_READINESS_GATE.md).

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
- **Readiness:** **eligible to begin** — V0 certified (ADR-0001); proceed under [`../docs/certification/V1_READINESS_GATE.md`](../docs/certification/V1_READINESS_GATE.md) (close the 3 entry conditions before the first V1 code merges).

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
