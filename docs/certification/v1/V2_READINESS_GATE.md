# V2 Readiness Gate

> **Document type:** Certification (V1→V2) · **Status:** Authoritative
> **Realizes:** NR-12 (version gate — a version may not begin until the prior gate
> is satisfied), AP-1 (vertical population, no re-layering)
> **Directive:** "Do not begin V2 automatically. Generate readiness findings,
> blockers, open risks, required remediation."

**V2 = Clinical Workflow Platform.** This gate states what must be true **before**
V2 work begins. **V2 is NOT authorized to start.** The findings below are the
entry conditions.

---

## 1. Readiness findings (current state)

- ✅ Offline pipeline is end-to-end, deterministic, patient-disjoint, uncertainty-
  aware, and auditable (V1 CERTIFIED-QUALIFIED).
- ✅ Application/Backend boundaries exist and are enforced (offline forms).
- ⚠️ Certification is **QUALIFIED**: synthetic data, minimal foundations, and
  unmechanized governance remain open (see Gap Analysis).

## 2. Blockers (must be CLOSED before V2 begins)

| ID | Blocker | Why it blocks V2 | Closes when |
|----|---------|------------------|-------------|
| B1 | **Real-EEG validation** (Gap G1 / Risk R1) | A clinical workflow on unvalidated synthetic-only methods is unsafe and would violate NR-15. | Real EEG ingested; patient-disjoint + domain-shift evaluation passes. |
| B2 | **Authoritative V1-P1…P4** (Gaps G2/G3) | V2 builds on data/DSP/intelligence/evaluation; provisional foundations can't bear clinical weight. | Full phases land behind current contracts; audit re-run green. |
| B3 | **Mechanized V0-P3 governance** (Gap G4) | V2 adds APIs/users/audit trail; boundary + quality enforcement must be a standalone gate, not just tests. | `.gcc/` import-rule scanner, debt registry, and version gates operate in CI. |
| B4 | **Unqualified V1 CERTIFIED** | The version gate (NR-12) forbids starting V2 on a qualified prior version. | Completion Report re-issued as unqualified CERTIFIED. |

## 3. Open risks carried into V2 (track, do not ignore)

- R1 synthetic→real gap, R2 calibration drift under shift, R3 conformal
  exchangeability, R4 governance mechanization — see `V1_RISK_REVIEW.md`.

## 4. Required remediation (ordered)

1. Land real-EEG data adapter behind `EEGDataset`; validate (B1).
2. Replace minimal foundations with authoritative V1-P1…P4 by **extension** (B2).
3. Mechanize `.gcc/` governance gate; move boundary/quality enforcement there (B3).
4. Re-run full audit; re-issue Completion Report as unqualified CERTIFIED (B4).
5. Only then open the V2 charter (clinical workflow, audit trail, API contracts).

## 5. Explicitly out of scope until the gate opens

Real-time/streaming, multi-user, FHIR/EMR, hospital integration, alerting,
clinical deployment, and any V2/V3/V4 feature. These remain **forbidden** in the
current version per the directive and the scope/version model.

## 6. Gate decision

**V2 entry: NOT GRANTED.** Re-evaluate when B1–B4 are closed and all tests +
verification scripts remain green.
