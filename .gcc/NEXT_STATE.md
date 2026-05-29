# NEXT STATE

> **Document type:** AI Operating System (V0-P4) · **Tier 3 (live)**
> **Status:** Living — updated whenever priorities, blockers, or transition criteria change.
> **Owner:** Founder · **Kept current by:** the active contributor (human or AI)
> **Update procedure:** Revise when the immediate plan changes; log in [`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md).
> **Last updated:** V0-P8 (V0 certified — V1 entry)
> **Companion:** [`CURRENT_STATE.md`](./CURRENT_STATE.md) (where we are)

This file answers: **"What happens next, and what must be true to get there?"**

---

## 1. Immediate Objectives (V1 entry)
**V0 is CERTIFIED WITH CONDITIONS (ADR-0001).** V1 (Offline EEG Platform) is
authorized to begin under [`../docs/certification/V1_READINESS_GATE.md`](../docs/certification/V1_READINESS_GATE.md).
Before the **first V1 code merges to `main`**, close the three entry conditions:
1. **Observe CI green** on the first V1 PR (verifies ASM-0006).
2. **Run a cold-onboarding test** with a fresh agent (verifies ASM-0001).
3. **Configure host branch protection** to match [`../docs/environment/BRANCH_PROTECTION_POLICY.md`](../docs/environment/BRANCH_PROTECTION_POLICY.md).

## 2. Upcoming Phases / Versions
- **V1 = Offline EEG Platform.** First workstreams (leaf-first, per the dependency graph):
  1. `preprocessing/` — deterministic, versioned transforms (AP-3/NR-9).
  2. `datasets/` — patient-indexed, leakage-safe access + LOSO split generation (AP-2/NR-3).
  3. `evaluation/` — patient-disjoint harness + calibration/coverage (AP-2/AP-4).
  4. `ml/` — baseline SZ/IIC detection with calibrated uncertainty (AP-4/NR-4).

## 3. Required Deliverables (to do real V1 work)
- [ ] **V1 toolchain ADR** — pin Python + dependency manager + lockfile + container
  ([`../docs/environment/TOOLCHAIN_STANDARD.md`](../docs/environment/TOOLCHAIN_STANDARD.md)).
- [ ] **Preprocessing spec (RFC→ADR)** — deterministic transform plan.
- [ ] **Evaluation protocol (RFC→ADR)** — patient-disjoint/LOSO + calibration/coverage.
- [ ] **Method-choice ADRs (drafted)** — split strategy; UQ technique (verify ASM-0003);
  model family (verify ASM-0004) — **no model adopted without patient-disjoint evidence.**

## 4. Upcoming Risks (watch as V1 begins; live: [`ACTIVE_RISKS.md`](./ACTIVE_RISKS.md))
- **AI/ARCH (RISK-0002/0003):** first real code is where boundary/hallucination risks
  go live — CI now catches drift; confirm it runs green.
- **TECH/REPRO:** preprocessing determinism is the foundation; design it test-first.
- **CLIN (RISK-0005):** activates when models exist — uncertainty + abstention by construction.

## 5. Dependencies (live detail: [`DEPENDENCY_REGISTRY.md`](./DEPENDENCY_REGISTRY.md))
- **V1 depends on V0 exit criteria** — ✅ satisfied (ADR-0001).
- `datasets`/`evaluation` depend on `preprocessing` first (leaf-first build order).
- Tooling: CI workflows now present; the V1 language toolchain is pinned by ADR at V1 start.

## 6. Blockers
- **None blocking V1 *initiation*** (V0 certified).
- **Hard rule:** the three §1 conditions **must close before the first V1 code merges
  to `main`** (CI green + cold-onboarding + host branch protection).

## 7. Transition Criteria (V0 → V1) — SATISFIED
- [x] All V0-P1…P8 deliverables complete and internally consistent.
- [x] Dependency graph acyclic; import rules explicit; boundaries documented.
- [x] Governance + AI OS + quality + context + environment in force and navigable.
- [x] **V0 certified** and recorded as **ADR-0001**.
- [x] No open Critical risk; no Blocker/Major gap; no unresolved consistency defect.

## 8. How To Update This File
When the plan changes, revise §1–§7, bump *Last updated*, and log it. Keep it
**actionable** — every item should be something a contributor can pick up and do.
