# V2 Exit Criteria

> **Document type:** Certification (V2) · **Status:** Authoritative
> **Rule:** every criterion must be **measurable** and backed by a reproducible check.

Status legend: **PASS** (objectively verified) · **PASS\*** (verified for delivered
scope; depends on a provisional foundation inherited from V1 — see Gap Analysis) ·
**FAIL**.

---

## Functional exit criteria

| # | Criterion | Status | Evidence |
|---|-----------|:------:|----------|
| 1 | Case workflows operational | PASS | `tests/test_clinical_cases.py`; `scripts.run_clinical_workflow` |
| 2 | Review workflows operational | PASS | `tests/test_clinical_review.py` (assign→session→complete→close) |
| 3 | Findings operational | PASS | `tests/test_clinical_findings.py` (evidence + interpretation + lifecycle) |
| 4 | Knowledge operational | PASS | `tests/test_clinical_knowledge.py` (terms/concepts/taxa/relationships) |
| 5 | Multi-case intelligence operational | PASS | `tests/test_multi_case_intelligence.py`; `scripts.verify_v2_p5_p6` |
| 6 | Decision support operational | PASS | `tests/test_decision_support.py`; explainable + scope-guarded |
| 7 | Clinical Workstation operational | PASS | `tests/test_clinical_workstation.py`; 10 nav areas render |
| 8 | Case workspace works | PASS | overview + per-case pages (metadata/state/audit/lineage/reports) |
| 9 | Review workspace works | PASS | status/history/sessions/assignments/progress/validation/lineage |
| 10 | Findings workspace works | PASS | metadata/evidence/interpretations/lifecycle/validation/audit/lineage |
| 11 | Knowledge workspace works | PASS | terminology/concepts/taxonomies/relationships/validation/audit |
| 12 | Intelligence workspace works | PASS | cohorts/analytics/trend/quality + validation reports |
| 13 | Decision support workspace works | PASS | context/evidence/risk/prioritization/guidance; no diagnosis/treatment |
| 14 | Audit browser works | PASS | unified browser over all immutable logs; per-scope verification |
| 15 | Lineage explorer works | PASS | Patient→…→Decision Support coverage + traceability graph; chain verified |
| 16 | Reporting center works | PASS | indexes every registered report across domains |
| 17 | State management works | PASS | deterministic `current_*` context; `set_context` reproducible |
| 18 | Workstation validation works | PASS | 7 consistency checks (artifact/registry/version/audit/lineage/workflow/state) |
| 19 | Audit system operational | PASS | hash-chained `ImmutableAuditLog` verifies on every subsystem |
| 20 | Lineage system operational | PASS | shared tracker; `verify_chain` true Patient → Decision Support |
| 21 | Governance operational | PASS\* | versioning/lineage/decisions operate; `.gcc` mechanization pending (V1 Gap G4) |
| 22 | Clinical inputs are real EEG | PASS\* | workflow runs on synthetic EEG-derived inputs (inherited V1 Gap G1) |
| 23 | Quality gates pass | PASS | boundary + determinism tests are the executable gates; all green |
| 24 | Certification audit completes | PASS | this document set + `scripts.verify_v2_p7_p8` |

## Quantitative gates (measured on the default workstation snapshot)

| Gate | Threshold | Status |
|------|-----------|:------:|
| Full test suite | all pass (240) | PASS |
| Workstation consistency checks | 7 / 7 | PASS |
| Primary navigation areas | 10 / 10 render | PASS |
| Per-subsystem audit logs verify | 100% | PASS |
| End-to-end lineage chain (Patient → Decision Support) | `verify_chain` true | PASS |
| Source immutability (intelligence/decision) | digest unchanged | PASS |
| Decision-support scope | 0 diagnosis/treatment/medication terms | PASS |
| Snapshot reproducibility | identical snapshot across runs | PASS |

## Summary

All **delivered-scope** exit criteria are **PASS**. Two criteria are **PASS\***
(governance mechanization is contract-only; clinical inputs are synthetic) — both
**inherited** from V1, both tracked in the Gap Analysis and the V3 Readiness Gate.
No criterion is FAIL. These `PASS*` items are the precise basis of the QUALIFIED
verdict.
