# NEXT STATE

> **Document type:** AI Operating System (V0-P4) · **Tier 3 (live)**
> **Status:** Living — updated whenever priorities, blockers, or transition criteria change.
> **Owner:** Founder · **Kept current by:** the active contributor (human or AI)
> **Update procedure:** Revise when the immediate plan changes; log in [`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md).
> **Last updated:** V0-P4 (this phase)
> **Companion:** [`CURRENT_STATE.md`](./CURRENT_STATE.md) (where we are)

This file answers: **"What happens next, and what must be true to get there?"**

---

## 1. Immediate Objectives (now → end of V0)
1. **Complete V0-P4** (this phase): finalize `.gcc/` OS artifacts (state, registers,
   protocols, templates, checklists).
2. **Run the V0 exit-criteria gate** ([`VERSION_STATUS.md`](./VERSION_STATUS.md) §V0)
   using the version-gate checklist
   ([`CHECKLISTS/version_gate_checklist.md`](./CHECKLISTS/version_gate_checklist.md)).
3. **Wire automated GCC checks** (boundary/import/acyclicity + doc consistency) as
   the first tooling task — convert specified rules into CI checks (tracked as
   `DEP`/early task, not a governance gap).
4. **Record the V0-completion ADR** in [`DECISION_REGISTRY.md`](./DECISION_REGISTRY.md).

## 2. Upcoming Phases / Versions
- **V0 gate → V1 entry.** V1 = Offline EEG Platform.
- **First V1 workstreams (in dependency order):**
  1. `preprocessing/` — deterministic, versioned transforms (AP-3/NR-9).
  2. `datasets/` — patient-indexed, leakage-safe access + LOSO split generation (AP-2/NR-3).
  3. `evaluation/` — patient-disjoint harness + calibration/coverage (AP-2/AP-4).
  4. `ml/` — baseline SZ/IIC detection with calibrated uncertainty (AP-4/NR-4).

## 3. Required Deliverables (to exit V0 and enter V1)
- [ ] V0 exit criteria verified and recorded (NR-12).
- [ ] Automated GCC + consistency checks operational in CI.
- [ ] V1 entry plan: preprocessing spec draft + evaluation protocol draft (as RFCs).
- [ ] Decision registry seeded with the method-choice ADRs V1 will need (model
  family candidate, UQ technique, split strategy) — drafted via RFC.

## 4. Upcoming Risks (watch as V1 begins; live: [`ACTIVE_RISKS.md`](./ACTIVE_RISKS.md))
- **AI/ARCH:** first real code is where boundary/hallucination risks become live —
  ensure GCC checks exist before substantial V1 code lands.
- **TECH/REPRO:** preprocessing determinism is the foundation; design it test-first.
- **AI:** prompt anti-patterns as implementation volume grows — enforce prompt
  standards ([`../docs/governance/AI_Governance.md`](../docs/governance/AI_Governance.md) §3).

## 5. Dependencies (live detail: [`DEPENDENCY_REGISTRY.md`](./DEPENDENCY_REGISTRY.md))
- **V1 depends on V0 exit criteria** (NR-12).
- `datasets` and `evaluation` depend on `preprocessing` existing first (build order
  follows the dependency graph, leaf-first).
- Tooling: a CI runner + the GCC check implementation (to be added).

## 6. Blockers
- **None blocking V0 completion.**
- **Soft pre-V1 blocker:** automated GCC checks should be in place before
  significant V1 code is merged (so drift is caught mechanically, not by eye).

## 7. Transition Criteria (V0 → V1)
V1 may begin **only when all** hold (Rule **NR-12**):
- [ ] All V0-P1…P4 deliverables complete and internally consistent.
- [ ] Dependency graph acyclic; import rules explicit; boundaries documented.
- [ ] Governance framework + AI OS in place and navigable.
- [ ] V0 exit-criteria gate recorded as an ADR.
- [ ] No open Critical risk; no unresolved consistency defect.

## 8. How To Update This File
When the plan changes, revise §1–§7, bump *Last updated*, and log it. Keep it
**actionable** — every item should be something a contributor can pick up and do.
