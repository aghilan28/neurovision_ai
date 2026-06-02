# V1 READINESS GATE

> **Document type:** Version 0 Certification (V0-P8) · **Tier 2**
> **Status:** Authoritative — the gate between V0 and V1
> **Owner:** Founder (Certification Authority)
> **Update procedure:** Governance-class change (ADR).
> **Enforces:** Rule **NR-12** (no version skip); [`../VERSION_EVOLUTION_MODEL.md`](../VERSION_EVOLUTION_MODEL.md)

Defines the **conditions for entering Version 1 (Offline EEG Platform).** V0 is
**CERTIFIED WITH CONDITIONS** ([`V0_COMPLETION_REPORT.md`](./V0_COMPLETION_REPORT.md)),
so V1 work **may begin**; this gate states exactly what must be true to begin and
what must **not** be done.

> **Premise:** V1 builds the first real code on the V0 foundation. The gate ensures
> that foundation is in force **before** code lands — so the first commit is governed,
> not retrofitted.

---

## 1. Conditions For Entering Version 1
V1 work may begin when **all** hold (status as of certification in brackets):
- [x] **V0 certified** (CERTIFIED WITH CONDITIONS) — ADR-0001 recorded.
- [x] **All mandatory V0 exit criteria MET** ([`V0_EXIT_CRITERIA.md`](./V0_EXIT_CRITERIA.md)).
- [x] **0 open Critical risks; 0 Blocker/Major gaps**.
- [x] **Governance/quality/context/environment frameworks in force** and navigable.
- [ ] **(Condition) CI observed green** on the first V1 PR (ASM-0006).
- [ ] **(Condition) Cold-onboarding test** run by a fresh agent (ASM-0001).
- [ ] **(Condition) Host branch protection configured** to match [`../environment/BRANCH_PROTECTION_POLICY.md`](../environment/BRANCH_PROTECTION_POLICY.md).

> The three open conditions are **entry tasks for the first V1 increment**, not
> blockers to starting V1 planning/first-module work. They must be **closed before
> the first V1 code merges to `main`.**

## 2. Forbidden Shortcuts (entering or doing V1)
- ❌ **No code merges that bypass CI/review** (NR-7); the first V1 PR **confirms** CI.
- ❌ **No non-patient-disjoint** evaluation, ever (NR-3) — patient-disjoint or it didn't happen.
- ❌ **No clinical output without calibrated uncertainty** (NR-4).
- ❌ **No nondeterministic preprocessing** on the production path (NR-9).
- ❌ **No forbidden import / no cycle / no rewrite** (NR-6/NR-8).
- ❌ **No new dependency without an ADR** + Dependency Registry entry (NR-2/NR-5).
- ❌ **No skipping** the V0 conditions "and fixing later."
- ❌ **No model adopted** without patient-disjoint evidence (ASM-0004).

## 3. Required Artifacts (before substantial V1 code)
- **Toolchain ADR** — pin the language runtime (Python) + dependency manager + lockfile + container ([`../environment/TOOLCHAIN_STANDARD.md`](../environment/TOOLCHAIN_STANDARD.md)).
- **Preprocessing spec (RFC→ADR)** — the deterministic transform plan (AP-3/NR-9).
- **Evaluation protocol (RFC→ADR)** — patient-disjoint/LOSO design (AP-2/NR-3) + calibration/coverage plan (AP-4).
- **Method-choice ADRs (drafted)** — split strategy, UQ technique (verify ASM-0003), model family (verify ASM-0004).

## 4. Required Approvals
- **Founder** approval for each architecture/governance/major change (NR-7; A2+ = ADR).
- The **V1 toolchain** and **first-module** ADRs approved before code merges.

## 5. Required Validations (active from the first V1 PR)
- **CI green** on all required workflows (documentation, architecture, governance, context; quality once code exists).
- **Determinism + invariant tests** for preprocessing (G4).
- **Patient-disjoint assertions** in evaluation (G5/VC-CLIN).
- **Reproducibility** of any reported result (NR-10).

## 6. Required Context State
- [`../../.gcc/CURRENT_STATE.md`](../../.gcc/CURRENT_STATE.md) shows **V0 certified / V1 active**.
- [`../../.gcc/NEXT_STATE.md`](../../.gcc/NEXT_STATE.md) lists the V1 first-increment objectives.
- [`../../.gcc/VERSION_STATUS.md`](../../.gcc/VERSION_STATUS.md) shows **V0 ✅ complete**, **V1 in progress**.
- Decision registry carries **ADR-0001** (V0 certification) + the V1 entry ADRs as drafted.

## 7. Required Repository State
- Clean: 0 broken links, 0 placeholders, ownership complete, 0 stray IDs (CI enforces).
- Branch protection on `main`; PR-only; required checks; human review.
- All V0 documents in force and unchanged except via governed change.

## 8. Gate Decision
When §1's open conditions are closed (at the first V1 increment), the Founder
records a brief **V1-start confirmation** (changelog + state update). Until then, V1
**planning and first-module drafting may proceed**; **no V1 code merges to `main`**
until the conditions are closed and CI is green.

## 9. Relationship To Other Documents
- Certification set: this directory · Version model: [`../VERSION_EVOLUTION_MODEL.md`](../VERSION_EVOLUTION_MODEL.md) §2
- Live state: [`../../.gcc/NEXT_STATE.md`](../../.gcc/NEXT_STATE.md), [`../../.gcc/VERSION_STATUS.md`](../../.gcc/VERSION_STATUS.md)

Changes to this document are governance-class and require an ADR.
