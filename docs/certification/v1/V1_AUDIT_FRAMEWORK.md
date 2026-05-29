# V1 Audit Framework

> **Document type:** Certification (V1) · **Status:** Authoritative
> **Realizes:** AP-8 (auditability), AP-11 (mechanized governance)

How the V1 audit is **conducted and reproduced**. The audit is evidence-driven:
every finding cites a test, a script result, or a registered artifact. Anyone can
re-run the audit and obtain the same verdict.

---

## 1. Audit method

1. **Static boundary audit.** AST-scan every module and assert the import DAG
   (NR-8): `preprocessing → datasets → ml → evaluation → backend → frontend`,
   with `ml ↛ evaluation`, `backend ↛ frontend`, and **`frontend` importing no
   domain module**. Evidence: `tests/test_boundaries.py`.
2. **Determinism & reproducibility audit.** Run the same configuration twice and
   assert identical content ids, weights bytes, inference ids, and report
   checksums. Evidence: reproducibility tests + `verify_v1` re-run check.
3. **Patient-disjoint audit.** Assert no patient spans train/calibration/test in
   any split and that benchmarking refuses non-patient-disjoint evaluation (NR-3).
   Evidence: split tests, dataset-intelligence leakage analysis, benchmark guard.
4. **Pipeline audit.** Execute the 15-stage orchestrator end to end; assert every
   stage succeeds, validation passes, and artifacts verify. Evidence:
   `tests/test_offline_inference.py`, `verify_v1`.
5. **Application audit.** Load a run with the import-pure frontend; assert app
   consistency validation passes and the static HTML renders deterministically.
   Evidence: `tests/test_research_app.py`.
6. **Governance audit.** Confirm registries reject silent overwrites, lineage
   chains verify, and decisions are recorded (ADR-0001/0002). Evidence: registry/
   lineage tests + decision records.

## 2. Evidence ledger (commands)

| Audit area | Command | Expected |
|-----------|---------|----------|
| All tests | `python -m pytest` | all pass |
| V1-P5/P6 criteria | `python -m scripts.verify_v1_p5_p6` | ALL CRITERIA SATISFIED |
| V1 (P7/P8 + e2e) criteria | `python -m scripts.verify_v1` | ALL CRITERIA SATISFIED |
| Offline pipeline run | `python -m scripts.run_offline_inference` | inference registered + artifacts verified |
| Research app render | `scripts.run_offline_inference --render-app` | deterministic HTML written |

## 3. Independence & honesty controls

- **Verifier ≠ producer.** Evaluation independently measures calibration/coverage;
  the audit relies on tests, not on the platform's own self-report alone.
- **No claim without evidence.** A criterion with no passing check is recorded as
  NOT MET, never assumed.
- **Provisional foundations are disclosed.** Where a subsystem is a minimal
  integration foundation (preprocessing/datasets/evaluation; see ADR-0001/0002),
  the audit marks dependent claims as *Provisional*, not *Strong*.

## 4. Reproducing the audit

```bash
python -m pip install -r requirements.txt   # numpy + pytest, pinned
python -m pytest                            # full suite (boundary/determinism/e2e)
python -m scripts.verify_v1_p5_p6           # V1-P5/P6 criteria
python -m scripts.verify_v1                 # V1-P7/P8 + certification criteria
```

All four must succeed for the Completion Report's verdict to hold.
