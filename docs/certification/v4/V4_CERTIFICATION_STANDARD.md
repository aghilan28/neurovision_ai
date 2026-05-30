# V4 Certification Standard

> Purpose: define the **objective standard** against which Version 4 (Governed
> Autonomy Foundation) is certified. Certification is **not** automatic — it is the
> outcome of the audit, readiness assessment, risk review, and gap analysis defined in
> this directory, executed by `scripts/verify_v4_p9_p10.py` and the test suite.

## 1. Scope of Version 4

Version 4 adds **governed autonomy intelligence** on top of the certified V0–V3
clinical/operational platform:

| Phase | Subsystem |
|-------|-----------|
| V4-P1 | Goal Intelligence Foundation (`backend/goal_intelligence`) |
| V4-P2 | Policy & Constraint Engine (`backend/policy_engine`) |
| V4-P3 | Planning Foundation (`backend/planning_foundation`) |
| V4-P4 | Task Intelligence Layer (`backend/task_intelligence`) |
| V4-P5 | Agent Coordination Framework (`backend/agent_coordination`) |
| V4-P6 | Execution Orchestration Layer (`backend/execution_orchestration`) |
| V4-P7 | Governance Intelligence Layer (`backend/governance_intelligence`) |
| V4-P8 | Autonomous Operations Workstation (`frontend/autonomous_operations_workstation`) |
| V4-P9 | Simulation & Scenario Layer (`backend/simulation_scenario`) |
| V4-P10 | Version 4 Certification (this directory) |

Version 4 is explicitly **not** autonomous action: every artifact is governed,
human-overseeable, and observation/evaluation-only where it concerns the future.

## 2. Certification principles

A subsystem is certifiable only if it is, with **objective evidence**:

1. **Deterministic** — no wall-clock, no randomness; identical inputs → identical outputs.
2. **Versioned** — content-addressed, chained versions.
3. **Traceable** — lineage parents reach the patient (`verify_chain`).
4. **Auditable** — every state change in the shared tamper-evident `ImmutableAuditLog`.
5. **Governed** — admitted only through its governance gate; policy/approval never bypassed.
6. **Explainable** — risks/forecasts carry factors + explanations.
7. **Bounded** — stays inside its phase scope (NR-13); no boundary violations.

## 3. Evidence classes

| Class | Evidence | Source |
|-------|----------|--------|
| E1 Tests | full suite green | `pytest` |
| E2 Verification | per-phase `verify_*` criteria all PASS | `scripts/verify_v4_p*.py` |
| E3 Lineage | `verify_chain` reaches patient from each subsystem | runtime |
| E4 Audit | `audit.verify()` true for every subsystem | runtime |
| E5 Determinism | repeated build → identical content ids | runtime |
| E6 Boundary | `tests/test_boundaries.py` green; lint clean on new code | `pytest` + `ruff` |
| E7 Governance | governance gates admit valid, reject invalid | runtime |

## 4. Certification grades

| Grade | Meaning | Condition |
|-------|---------|-----------|
| **CERTIFIED** | Version 4 is complete and safe | all exit criteria met; no Critical/High gaps open |
| **CONDITIONAL** | usable with documented conditions | all Critical met; ≤ defined Moderate gaps, each with remediation |
| **NOT CERTIFIED** | not ready | any Critical exit criterion unmet |

## 5. Authority

The objective certification outcome is produced by `scripts/verify_v4_p9_p10.py`
(criterion 25). This standard is descriptive of the bar; the script is the executable
judge. Certification claims in `V4_COMPLETION_REPORT.md` MUST cite the script's output.
