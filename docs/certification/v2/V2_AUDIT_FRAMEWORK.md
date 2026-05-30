# V2 Audit Framework

> **Document type:** Certification (V2) · **Status:** Authoritative
> **Realizes:** AP-8 (auditability), AP-11 (mechanized governance)

How the V2 audit is **conducted and reproduced**. The audit is evidence-driven:
every finding cites a test, a script result, or a registered artifact. Anyone can
re-run the audit and obtain the same verdict.

---

## 1. Audit categories, procedures, evidence

| # | Category | Procedure | Evidence |
|---|----------|-----------|----------|
| 1 | **Case Audit** | Create/transition a case through its lifecycle; assert each transition is audited, lineage-extended, version-bumped, registry-synced. | `tests/test_clinical_cases.py`, `scripts.run_clinical_workflow` |
| 2 | **Review Audit** | Run assign → session → complete → close; assert tracking + immutable audit + lineage. | `tests/test_clinical_review.py` |
| 3 | **Finding Audit** | Create finding + evidence + interpretation; assert mandatory-evidence rule and lifecycle. | `tests/test_clinical_findings.py` |
| 4 | **Knowledge Audit** | Add terms/concepts/taxa/relationships; assert versioned, audited, validated. | `tests/test_clinical_knowledge.py` |
| 5 | **Intelligence Audit** | Build cohort/analytics/trend/quality over a population; assert no artifact outside registry + source immutability. | `tests/test_multi_case_intelligence.py`, `scripts.verify_v2_p5_p6` |
| 6 | **Decision Audit** | Process a case; assert explainability + scope guard (no diagnosis/treatment) + lineage to patient. | `tests/test_decision_support.py`, `scripts.verify_v2_p5_p6` |
| 7 | **Workstation Audit** | Build the snapshot + view; assert the 7 consistency checks pass and HTML is deterministic; assert the workstation imports no domain module. | `tests/test_clinical_workstation.py`, `tests/test_boundaries.py` |
| 8 | **Governance Audit** | Confirm registries reject silent overwrites, lineage chains verify, decisions recorded (ADR-0003…0006). | registry/lineage tests + decision records |
| 9 | **Quality Audit** | Run the full suite; the boundary + determinism tests are the executable quality gates. | `python -m pytest` |
| 10 | **Context Audit** | Confirm navigation context references only existing artifacts (state consistency). | `tests/test_clinical_workstation.py::test_state_consistency_*` |

## 2. Audit checklists (per category)

Each category passes only if **all** of its checks pass:

- **Integrity** — the relevant immutable audit log `verify()`s true.
- **Traceability** — the relevant lineage chain `verify_chain()`s true to the patient root.
- **Registration** — the artifact exists in its registry (nothing outside the registry).
- **Versioning** — the artifact carries a content-addressed version.
- **Validation** — the subsystem's own validator reports `ok`.
- **Scope** (decision/intelligence) — no out-of-scope content; source truth unmodified.

## 3. Audit evidence requirements

- **No claim without evidence.** A criterion with no passing check is recorded as
  NOT MET, never assumed.
- **Verifier ≠ producer.** Workstation validation reads the validation/audit/lineage
  facts the backend recorded; it does not re-derive domain truth.
- **Provisional foundations are disclosed.** Inherited V1 provisional items
  (synthetic data, unmechanized governance) mark dependent claims *Adequate*, not
  *Strong* (see Gap Analysis / Readiness Assessment).

## 4. Audit escalation rules

| Finding severity | Action |
|------------------|--------|
| **Blocking** (an exit criterion FAILs / an audit log fails to verify / a boundary violation) | Halt certification; record NOT CERTIFIED; open a remediation item. |
| **Major** (a delivered-scope check is flaky or a registry/lineage inconsistency) | Block the affected dimension; require fix + re-run before sign-off. |
| **Minor** (a provisional foundation; cosmetic) | Record in Gap Analysis with remediation; permit QUALIFIED. |

## 5. Reproducing the audit

```bash
python -m pip install numpy            # pinned; only runtime dep
python -m pytest                       # full suite (240 tests; boundary/determinism/e2e)
python -m scripts.verify_v2_p3_p4      # V2-P3/P4 criteria
python -m scripts.verify_v2_p5_p6      # V2-P5/P6 criteria
python -m scripts.verify_v2_p7_p8      # V2-P7/P8 + certification criteria
python -m scripts.build_workstation_snapshot --out workstation_snapshot.json
```

All must succeed for the Completion Report's verdict to hold.
