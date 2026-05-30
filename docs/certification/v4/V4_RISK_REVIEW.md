# V4 Risk Review

> Structured review of the risks across Version 4, each with a likelihood/impact
> rating, the existing mitigation, residual risk, and the objective evidence the
> mitigation holds.

Ratings: Likelihood/Impact ∈ {Low, Moderate, High}. Residual is after mitigation.

## 1. Architecture risks

| Risk | L | I | Mitigation | Residual | Evidence |
|------|---|---|------------|----------|----------|
| A later phase redesigns a prior phase | Low | High | additive-only changes; full suite re-run | Low | E1 (530+ tests green), git diff additive |
| Parallel lineage/audit systems emerge | Low | High | single shared `LineageTracker` + `ImmutableAuditLog` reused everywhere | Low | E4, code review |
| Boundary erosion (frontend imports domain) | Low | High | `tests/test_boundaries.py`; snapshot-only frontend | Low | E6 |

## 2. Policy / Planning / Task risks

| Risk | L | I | Mitigation | Residual | Evidence |
|------|---|---|------------|----------|----------|
| Policy evaluation bypassed | Low | Critical | every entity admitted via policy decider + gate | Low | E2 (`verify_v4_p1_p2`), E7 |
| Plan/task without governing policy | Low | Moderate | governance gate `policy_references` check; violation intelligence | Low | E2, E7 |
| Task dependency mis-modelling | Low | Moderate | deterministic dependency evaluation; simulation dependency risk | Low | E2, sim risk |

## 3. Agent / Execution risks

| Risk | L | I | Mitigation | Residual | Evidence |
|------|---|---|------------|----------|----------|
| Agent gains autonomous authority | Low | Critical | agents describe capability only; `_AUTONOMY_ATTRS` gate | Low | `verify_v4_p5_p6`, E7 |
| Execution bypasses authorization | Low | Critical | execution gate requires authorization; negative tests | Low | E2, E7 |

## 4. Governance risks

| Risk | L | I | Mitigation | Residual | Evidence |
|------|---|---|------------|----------|----------|
| Governance intelligence modifies governance | Low | Critical | observe-only gate; observe-only invariant test | Low | `verify_v4_p7_p8`, E7 |
| Unreviewed escalations / violations | Low | High | monitoring surfaces them; human-oversight workstation | Low | E2 |

## 5. Simulation risks

| Risk | L | I | Mitigation | Residual | Evidence |
|------|---|---|------------|----------|----------|
| Simulation executes / mutates production | Low | Critical | evaluate-only gate rejects action statuses | Low | `verify_v4_p9_p10`, E7 |
| Non-deterministic simulation | Low | High | no randomness/wall-clock; content-addressed | Low | E5 |
| Forecast mistaken for fact | Low | Moderate | forecasts are projections (`would_*`) with confidence + explanation | Low | sim reports |

## 6. Operational risks

| Risk | L | I | Mitigation | Residual | Evidence |
|------|---|---|------------|----------|----------|
| Operator acts on stale view | Low | Moderate | snapshot is deterministic + content-addressed | Low | E5 |
| Lost traceability for an action | Low | High | every control declares audit+lineage+governance records | Low | E3/E4 |

## 7. Unknown risks

Addressed by defense-in-depth: tamper-evident audit, full lineage to patient, strict
gates, and determinism mean unknown failures are detectable and reproducible. Tracked
as a standing Moderate item with no current evidence of materialization.

## 8. Future risks (V5 and beyond) — out of scope for V4

Distributed intelligence, multi-site federation, self-modifying systems, autonomous
goal/policy creation, autonomous governance modification, realtime EEG, hospital
deployment. These are **explicitly forbidden** in V4 and gated by `V5_READINESS_GATE.md`.

## 9. Summary

No **Critical** or **High** risk has materialized: every Critical risk has a tested
mitigation with passing objective evidence. Residual risk across the matrix is **Low**.
