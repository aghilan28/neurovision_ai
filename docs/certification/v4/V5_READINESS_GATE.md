# V5 Readiness Gate

> The **measurable entry criteria** for Version 5. Version 5 work MUST NOT begin until
> every condition below is met with objective evidence. This gate exists to prevent
> scope-skipping (NR-12) and out-of-scope work (NR-13).

## 1. Conditions for entering Version 5

| # | Condition | Measure (objective) |
|---|-----------|---------------------|
| G1 | Version 4 certified | `V4_COMPLETION_REPORT.md` outcome = CERTIFIED, justified by `verify_v4_p9_p10` `ALL CRITERIA PASS` |
| G2 | All V4 exit criteria met | `V4_EXIT_CRITERIA.md` EC-1…EC-18 all met |
| G3 | No open Critical/High/Moderate gaps | `V4_GAP_ANALYSIS.md` shows 0 at those severities |
| G4 | Full suite green | `pytest` → 0 failures |
| G5 | All verify scripts green | every `scripts/verify_v4_p*` → `ALL CRITERIA PASS` |
| G6 | Determinism holds | repeat builds → identical content ids |

## 2. Required artifacts (must pre-exist, certified)

Goals, Policies/Constraints, Plans, Tasks, Agents, Executions, Governance Intelligence,
Human Oversight Workstation, Simulation & Scenario Layer, and the full V4 certification
set — all present, governed, and lineage-traced to the patient.

## 3. Required validation state

Every V4 subsystem's validator returns `ok` for representative artifacts; every
governance gate admits valid and rejects invalid artifacts.

## 4. Required governance state

Policy evaluation and approval workflows are never bypassed; governance intelligence is
observe-only; agents hold no autonomous authority; simulation is evaluate-only. All
enforced by gates with passing evidence.

## 5. Required audit state

Every subsystem's `ImmutableAuditLog` chain verifies; the chain is shared (no parallel
audit). Tamper-evidence demonstrated by `audit.verify()`.

## 6. Required repository state

Additive-only change history for V4; `ruff` clean on all V4 code; `tests/test_boundaries.py`
green; lineage reaches the patient from every subsystem including simulation.

## 7. Required safety state

The full deliverable chain Patient → … → Governance Intelligence → Human Oversight →
Simulation → Certification verifies end-to-end, deterministically.

## 8. Forbidden shortcuts (gate violations)

The following **void** the gate if attempted to enter V5:

- Skipping any V4 phase or certification step (NR-12).
- Implementing V5 capability inside V4 (NR-13).
- Autonomous goal creation, autonomous policy creation, or autonomous governance
  modification.
- Self-modifying systems; distributed intelligence; multi-site federation.
- Realtime EEG systems or hospital-deployment systems introduced as a "shortcut".
- Certifying without the objective evidence of §1 (no self-attestation).

## 9. Gate decision rule

Entry to Version 5 is **PERMITTED** iff G1–G6 hold and no forbidden shortcut has been
taken. Otherwise entry is **DENIED**. The decision must cite the `verify_v4_p9_p10`
output and the test-suite result; it is never granted by assertion.
