# V3 Readiness Gate

> **Document type:** Certification (V2→V3) · **Status:** Authoritative
> **Realizes:** NR-12 (version gate — a version may not begin until the prior gate
> is satisfied), AP-1 (vertical population, no re-layering)
> **Directive:** "Define conditions for entering Version 3. Create measurable entry
> criteria."

**V3 = (per the version model) the near-real-time / advanced operational tier.**
This gate states what must be true **before** V3 work begins. **V3 is NOT
authorized to start.** The criteria below are the entry conditions, and each is
**measurable**.

---

## 1. Readiness findings (current state)

- ✅ V2 clinical-workflow platform is end-to-end, deterministic, fully audited,
  lineage-complete to the patient, decision-support-only, and presentation-pure
  (V2 CERTIFIED-QUALIFIED).
- ✅ A unified Clinical Workstation operates over all six V2 subsystems.
- ⚠️ Certification is **QUALIFIED**: synthetic data, unmechanized governance, and
  in-memory persistence remain open (inherited; see Gap Analysis).

## 2. Entry criteria (measurable; must all be MET before V3 begins)

| ID | Criterion | Measurable test |
|----|-----------|-----------------|
| E1 | **Unqualified V2 CERTIFIED.** | `V2_COMPLETION_REPORT.md` re-issued with verdict CERTIFIED (no QUALIFIED), all verify scripts + `pytest` green. |
| E2 | **Real-EEG validated workflow.** | A real-EEG case is driven through Case→…→Decision Support; patient-disjoint + domain-shift evaluation passes (closes G1/R1). |
| E3 | **Mechanized governance gate.** | `.gcc/` import-rule scanner + debt registry + version gates run in CI and fail the build on violation (closes G2/R3). |
| E4 | **Durable, checksummed persistence.** | V2 registries/audit/lineage persist to a checksummed on-disk store; reload reproduces identical signatures (closes G3/R4). |
| E5 | **Snapshot is a registered artifact.** | The workstation snapshot is written with a sha256 manifest and verified on load (closes G4). |
| E6 | **Audit state clean.** | Every subsystem audit log `verify()`s true and the end-to-end lineage `verify_chain()`s true on the real-EEG workflow. |
| E7 | **Governance state clean.** | All decision records (ADR-0003…0006 + any new) accepted; no open Blocking/Major gap. |
| E8 | **Repository state clean.** | Full suite green; no boundary violation; deterministic artifacts; pinned deps. |

## 3. Required artifacts / approvals / validation / audit / repository state

- **Required artifacts:** real-EEG validated run; durable V2 store; checksummed
  snapshot manifest; re-issued unqualified V2 Completion Report.
- **Required approvals:** human sign-off on the re-issued certification (NR-7).
- **Required validation:** `pytest` + `verify_v2_p3_p4` + `verify_v2_p5_p6` +
  `verify_v2_p7_p8` (+ `verify_v2`) all green.
- **Required audit state:** all logs verify; lineage complete to patient on real data.
- **Required repository state:** clean boundaries (DAG enforced), pinned env.
- **Required governance state:** mechanized `.gcc/` gate operating in CI.

## 4. Open risks carried toward V3 (track, do not ignore)

- R1 synthetic→real gap, R2 decision-support over-reliance, R3 governance
  mechanization, R4 in-memory persistence — see `V2_RISK_REVIEW.md`.

## 5. Forbidden shortcuts

- ❌ Declaring V3 entry while V2 is only QUALIFIED (violates NR-12).
- ❌ Introducing FHIR/HL7/EMR, hospital integration, real-time/streaming EEG, or
  deployment infrastructure **before** the gate opens (Scope/forbidden-work list).
- ❌ Mechanizing governance "later" — it is an explicit entry criterion (E3).
- ❌ Substituting synthetic for real-EEG validation (E2 is not waivable).
- ❌ Bypassing the version gate by re-scoping V3 features into V2.

## 6. Gate decision

**V3 entry: NOT GRANTED.** Re-evaluate when **E1–E8** are MET and all tests +
verification scripts remain green.
