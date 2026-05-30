# V4 Readiness Gate

> **Document type:** Certification (V3→V4) · **Status:** Authoritative
> **Realizes:** NR-12 (version gate — a version may not begin until the prior gate
> is satisfied), AP-1 (vertical population, no re-layering)
> **Directive:** "Define conditions for entering Version 4. Create measurable entry criteria."

**V4 = (per the version model) the deployment / hospital-grade / real-time tier.**
This gate states what must be true **before** V4 work begins. **V4 is NOT
authorized to start.** Each criterion below is **measurable**.

---

## 1. Readiness findings (current state)

- ✅ V3 operational-intelligence platform is end-to-end, deterministic, fully
  audited, lineage-complete to the patient, and presentation-pure (V3 CERTIFIED-QUALIFIED).
- ✅ A unified Operational Intelligence Workstation operates over all six V3 subsystems.
- ⚠️ Certification is **QUALIFIED**: synthetic data, unmechanized governance, and
  in-memory persistence remain open (inherited; see `V3_GAP_ANALYSIS.md`).

## 2. Entry criteria (measurable; must all be MET before V4 begins)

| ID | Criterion | Measurable test |
|----|-----------|-----------------|
| E1 | **Unqualified V3 CERTIFIED.** | `V3_COMPLETION_REPORT.md` re-issued with verdict CERTIFIED (no QUALIFIED); all verify scripts + `pytest` green. |
| E2 | **Real-EEG validated operation.** | A real-EEG case is driven through Case→…→Recommendations; patient-disjoint + domain-shift evaluation passes (closes G1/R1). |
| E3 | **Mechanized governance gate.** | `.gcc/` import-rule scanner + scope/debt gates run in CI and fail the build on violation (closes G2/R3). |
| E4 | **Durable, checksummed persistence.** | V3 registries/audit/lineage persist to a checksummed on-disk store; reload reproduces identical signatures (closes G3/R4). |
| E5 | **Snapshot is a registered artifact.** | The operational-workstation snapshot is written with a sha256 manifest and verified on load (closes G4). |
| E6 | **Audit state clean.** | Every subsystem audit log `verify()`s true and the end-to-end lineage `verify_chain()`s true on the real-EEG operation. |
| E7 | **Governance state clean.** | All decision records (ADR-0007…0010 + any new) accepted; no open Blocking/Major gap. |
| E8 | **Repository state clean.** | Full suite green; no boundary violation; deterministic artifacts; pinned deps. |

## 3. Required artifacts / approvals / validation / audit / repository state

- **Required artifacts:** real-EEG validated run; durable V3 store; checksummed
  snapshot manifest; re-issued unqualified V3 Completion Report.
- **Required approvals:** human sign-off on the re-issued certification (NR-7).
- **Required validation:** `pytest` + `verify_v3_p1_p2` + `verify_v3_p3_p4` +
  `verify_v3_p5_p6` + `verify_v3_p7_p8` all green.
- **Required audit state:** all logs verify; lineage complete to the patient on real data.
- **Required repository state:** clean boundaries (DAG enforced), pinned env.
- **Required governance state:** mechanized `.gcc/` gate operating in CI.

## 4. Open risks carried toward V4 (track, do not ignore)

- R1 synthetic→real gap, R3 governance mechanization, R4 in-memory persistence —
  see `V3_RISK_REVIEW.md`.

## 5. Forbidden shortcuts

- ❌ Declaring V4 entry while V3 is only QUALIFIED (violates NR-12).
- ❌ Introducing real-time/streaming EEG, autonomous agents, multi-site federation,
  distributed intelligence, or FHIR/HL7/EMR/deployment infrastructure **before** the
  gate opens (Scope/forbidden-work list).
- ❌ Mechanizing governance "later" — it is an explicit entry criterion (E3).
- ❌ Substituting synthetic for real-EEG validation (E2 is not waivable).
- ❌ Bypassing the version gate by re-scoping V4 features into V3.

## 6. Gate decision

**V4 entry: NOT GRANTED.** Re-evaluate when **E1–E8** are MET and all tests +
verification scripts remain green.
