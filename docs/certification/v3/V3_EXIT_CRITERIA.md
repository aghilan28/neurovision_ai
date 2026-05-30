# V3 Exit Criteria

> **Document type:** Certification (V3) · **Status:** Issued
> **Rule:** every criterion is **measurable** and verified by a reproducible command
> or registered artifact. A criterion is PASS only if objectively demonstrated.

These are the delivered-scope exit criteria for Version 3. All are **PASS** on the
audited commit.

---

## 1. Exit criteria (measurable)

| ID | Criterion | Measurable test | Result |
|----|-----------|-----------------|--------|
| X1 | **Events operational.** | `verify_v3_p1_p2` event criteria PASS; event audit verifies. | ✅ PASS |
| X2 | **Timelines operational.** | `verify_v3_p1_p2` temporal criteria PASS; temporal audit verifies. | ✅ PASS |
| X3 | **Workflows operational.** | `verify_v3_p3_p4` workflow criteria PASS; `test_workflow_intelligence.py` green. | ✅ PASS |
| X4 | **Graph operational.** | `verify_v3_p3_p4` graph criteria PASS; no graph-only truth (every node has a source). | ✅ PASS |
| X5 | **Analytics operational.** | `verify_v3_p5_p6` analytics criteria (1–9) PASS; gate forbids non-derived analytics. | ✅ PASS |
| X6 | **Recommendations operational.** | `verify_v3_p5_p6` recommendation criteria (10–17) PASS; evidence+analytics-linked. | ✅ PASS |
| X7 | **Workstation operational.** | `verify_v3_p7_p8` (1–12) PASS; ten areas render; six consistency checks pass. | ✅ PASS |
| X8 | **Audit system operational.** | every subsystem audit log `verify()`s true; unified audit browser covers all six. | ✅ PASS |
| X9 | **Lineage system operational.** | `verify_chain` from a recommendation reaches the patient; `representative_chain.verified` true. | ✅ PASS |
| X10 | **Governance operational.** | ADR-0007…0010 accepted; one shared lineage/audit (no parallel systems). | ✅ PASS |
| X11 | **Quality gates pass.** | `python -m pytest` → **363 passed**; `ruff` clean on new code; artifacts reproducible. | ✅ PASS |
| X12 | **Boundaries intact.** | `tests/test_boundaries.py` green; `frontend/operational_workstation` imports no domain module. | ✅ PASS |
| X13 | **Scope discipline.** | no realtime/autonomous/multi-site/streaming/FHIR/HL7/EMR/V4 code (Version Readiness). | ✅ PASS |
| X14 | **Deterministic + reproducible.** | snapshot byte-identical across runs; view-model + HTML are pure functions of the snapshot. | ✅ PASS |

## 2. Unified-environment deliverable

The required chain operates through one unified operational environment:

```
Patient → Case → Review → Finding → Knowledge → Decision → Event → Timeline →
Workflow → Graph → Analytics → Recommendations → Operational Workstation →
Audit Trail → Lineage Trail
```

Verified by `verify_v3_p7_p8` (criterion 20) and the snapshot's
`representative_chain` (anchor = a real recommendation; verified true).

## 3. Commands (reproducible)

```bash
python -m pytest                                  # 363 passed
python -m scripts.verify_v3_p1_p2                 # ALL CRITERIA PASS
python -m scripts.verify_v3_p3_p4                 # ALL CRITERIA PASS
python -m scripts.verify_v3_p5_p6                 # ALL CRITERIA PASS
python -m scripts.verify_v3_p7_p8                 # ALL CRITERIA PASS (21/21)
python -m scripts.build_operational_workstation_snapshot --out op.json  # chain verified
```

## 4. Exit verdict

**All delivered-scope exit criteria PASS.** Remaining items (G1–G4) are inherited
foundational dependencies recorded in the Gap Analysis; they qualify (not block)
the certification.
