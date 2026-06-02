# V4 Exit Criteria

> Every criterion is **measurable** and mapped to objective evidence executed by the
> test suite and the verification scripts. Version 4 exits (is certifiable) only when
> **all** criteria are met.

## 1. Operational exit criteria

| # | Exit criterion | Measure | Evidence |
|---|----------------|---------|----------|
| EC-1 | Goals operational | goals build/govern/validate; lineage→patient | `verify_v4_p1_p2` PASS |
| EC-2 | Policies operational | policies/constraints evaluate; deciders gate all entities | `verify_v4_p1_p2` PASS |
| EC-3 | Plans operational | plans derive from goals; govern + validate | `verify_v4_p3_p4` PASS |
| EC-4 | Tasks operational | tasks derive from plans; dependencies modelled | `verify_v4_p3_p4` PASS |
| EC-5 | Agents operational | agents minted, capability-matched, assigned | `verify_v4_p5_p6` PASS |
| EC-6 | Executions operational | executions reference approved assignments; authorized | `verify_v4_p5_p6` PASS |
| EC-7 | Governance operational | governance intelligence observes all kinds; validates | `verify_v4_p7_p8` PASS |
| EC-8 | Human oversight operational | workstation: 11 areas, governed controls, consistency | `verify_v4_p7_p8` PASS |
| EC-9 | Simulation operational | scenario/simulation/forecast/comparison/risk work | `verify_v4_p9_p10` 1–12 PASS |
| EC-10 | Audit system operational | every subsystem audit chain verifies | `audit.verify()` all true |
| EC-11 | Lineage system operational | `verify_chain` reaches patient incl. from simulation | runtime E3 |

## 2. Safety & integrity exit criteria

| # | Exit criterion | Measure | Evidence |
|---|----------------|---------|----------|
| EC-12 | Governance gates pass | valid admitted; invalid rejected | `verify_v4_p9_p10` #20 |
| EC-13 | Audit trails pass | tamper-evident chains intact | `verify_v4_p9_p10` #21 |
| EC-14 | All tests pass | 0 failures | `verify_v4_p9_p10` #22 |
| EC-15 | V4 lineage intact | prior-phase lineage/validation unbroken | `verify_v4_p9_p10` #23 |
| EC-16 | No boundary violations | frontend imports no domain; V4 lint clean | `verify_v4_p9_p10` #24 |
| EC-17 | Determinism | repeat build → identical content ids | runtime E5 |
| EC-18 | Full deliverable chain | Patient→…→Simulation verifies end-to-end | `verify_v4_p9_p10` #7, e2e test |

## 3. Exit rule

Version 4 **EXITS** iff EC-1 … EC-18 are all met (each binary, evidence-backed). The
binary evaluation and the aggregate are produced by `scripts/verify_v4_p9_p10.py`. Any
unmet criterion → not certified.
