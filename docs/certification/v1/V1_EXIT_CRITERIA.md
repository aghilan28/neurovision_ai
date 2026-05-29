# V1 Exit Criteria

> **Document type:** Certification (V1) · **Status:** Authoritative
> **Rule:** every criterion must be **measurable** and backed by a reproducible check.

Status legend: **PASS** (objectively verified) · **PASS\*** (verified for delivered
scope; depends on a provisional foundation — see Gap Analysis) · **FAIL**.

---

## Functional exit criteria

| # | Criterion | Status | Evidence |
|---|-----------|:------:|----------|
| 1 | EEG ingestion works | PASS\* | orchestrator `dataset_ingestion` stage; synthetic source (real EEG pending). |
| 2 | Preprocessing works (deterministic) | PASS | `tests/test_foundations.py`; preprocessing signature stable. |
| 3 | Patient-disjoint evaluation works | PASS | split tests + `evaluation` harness; leakage analysis. |
| 4 | Benchmarking works | PASS | `tests/test_evaluation_benchmark.py`; benchmark registered in pipeline. |
| 5 | Calibration works | PASS | `tests/test_uncertainty.py`; calibration output in every run. |
| 6 | Conformal prediction works | PASS | conformal coverage ≥ target on patient-disjoint test. |
| 7 | Coverage validation works | PASS | coverage tracker reliable flag; `tests/test_uncertainty.py`. |
| 8 | Offline inference works (end to end) | PASS | 15-stage orchestrator; `tests/test_offline_inference.py`. |
| 9 | Offline application works | PASS | import-pure app; `tests/test_research_app.py`; deterministic HTML. |
| 10 | Output contracts work | PASS | 10 typed output contracts validated + registered. |
| 11 | Inference registry works | PASS | no inference outside registry; silent-overwrite rejected. |
| 12 | Artifact system works | PASS | checksummed artifacts; `verify_directory` detects tampering. |
| 13 | Lineage works | PASS | content-addressed chain; `verify_chain` true end to end. |
| 14 | Reports work | PASS | 6 backend reports + app HTML; reproducible. |
| 15 | Visualizations work | PASS | 11 visualization specs rendered as inline SVG. |
| 16 | Upload workflow works | PASS | metadata/quality/readiness from dataset-intelligence. |
| 17 | Benchmark workflow works | PASS | benchmark registry + evaluation + split shown. |
| 18 | Audit workflow works | PASS | lineage/artifacts/registries/versions/trails shown. |
| 19 | Deterministic reproducibility works | PASS | same config → identical ids/checksums (tests + `verify_v1`). |
| 20 | Governance works | PASS\* | versioning/lineage/decisions operate; `.gcc` mechanization pending (V0-P3). |
| 21 | V0 quality gates pass | PASS | boundary + determinism tests are the executable gates; all green. |
| 22 | Certification audit completes | PASS | this document set + `verify_v1`. |

## Quantitative gates (measured on a default offline run)

| Gate | Threshold | Status |
|------|-----------|:------:|
| Pipeline stages succeeded | 15 / 15 | PASS |
| Inference validation checks | 7 / 7 | PASS |
| App consistency checks | 5 / 5 | PASS |
| Conformal coverage vs target (0.90) | observed ≥ target − 0.05 | PASS |
| Artifact integrity | 100% checksums verify | PASS |
| Reproducibility | identical content signatures across runs | PASS |

## Summary

All **delivered-scope** exit criteria are **PASS**. Two criteria are **PASS\***
(EEG ingestion is synthetic; governance mechanization is contract-only). No
criterion is FAIL. These `PASS*` items are the precise basis of the QUALIFIED
verdict and are tracked in the Gap Analysis and V2 Readiness Gate.
