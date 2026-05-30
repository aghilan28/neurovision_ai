# V4 Readiness Assessment

> Measurable readiness scoring per subsystem, with evidence requirements and pass/fail
> thresholds. Scores are produced **objectively** by `scripts/verify_v4_p9_p10.py`
> (the readiness scorecard) — this document defines the rubric.

## 1. Scoring model

Each readiness dimension is scored in `[0.0, 1.0]` as the fraction of its required
evidence checks that pass:

```
readiness(dimension) = (checks passed) / (checks required)
```

A dimension **PASSES** iff `readiness == 1.0` (every required check passes). The bar is
intentionally strict: partial evidence is not readiness.

| Threshold | Value |
|-----------|-------|
| Dimension pass | `readiness == 1.0` |
| Version pass | every dimension passes |
| Critical dimensions | all of them (no dimension is optional) |

## 2. Required evidence per dimension

| # | Readiness dimension | Required evidence | Pass threshold |
|---|---------------------|-------------------|----------------|
| 1 | Goal Readiness | goals build, govern, validate; lineage reaches patient; `verify_v4_p1_p2` PASS | 1.0 |
| 2 | Policy Readiness | policies/constraints evaluate; deciders gate goals/plans/tasks/agents/executions; `verify_v4_p1_p2` PASS | 1.0 |
| 3 | Planning Readiness | plans derive from goals; govern + validate; `verify_v4_p3_p4` PASS | 1.0 |
| 4 | Task Readiness | tasks derive from plans; dependencies modelled; `verify_v4_p3_p4` PASS | 1.0 |
| 5 | Agent Readiness | agents minted, capability-matched, assigned; `verify_v4_p5_p6` PASS | 1.0 |
| 6 | Execution Readiness | executions reference approved assignments; authorized; `verify_v4_p5_p6` PASS | 1.0 |
| 7 | Governance Readiness | governance intelligence observes all kinds; validation ok; `verify_v4_p7_p8` PASS | 1.0 |
| 8 | Workstation Readiness | 11 areas render; governed controls; 6 consistency checks; `verify_v4_p7_p8` PASS | 1.0 |
| 9 | Simulation Readiness | scenario/simulation/forecast/comparison/risk work; validation ok; `verify_v4_p9_p10` 1–12 PASS | 1.0 |
| 10 | Repository Readiness | full test suite green; ruff clean on V4 code; boundary test green | 1.0 |
| 11 | Version Readiness | end-to-end chain Patient→…→Simulation verifies; all audits verify; determinism holds | 1.0 |

## 3. Evidence requirements (objective)

- **E1** `pytest` full suite: 0 failures.
- **E2** every `scripts/verify_v4_p*.py`: `RESULT: ALL CRITERIA PASS`.
- **E3** `tracker.verify_chain(node)` true from a goal, an execution, a governance-intelligence
  record, and a simulation; the simulation chain contains the full spine
  `{patient, goal, policy, plan, task, agent, execution, governance_intelligence, scenario, simulation}`.
- **E4** `audit.verify()` true for goals, policies, plans, tasks, agents, executions,
  governance intelligence, and simulation logs.
- **E5** repeated deterministic build yields identical content ids.

## 4. Pass/fail thresholds

- A dimension with any missing/failed required evidence scores `< 1.0` → **FAIL**.
- Version 4 readiness = **PASS** iff all 11 dimensions PASS.
- The readiness scorecard and overall PASS/FAIL are emitted by
  `scripts/verify_v4_p9_p10.py` (criteria 14 & 25). This document is not the judge —
  the script is.
