# V1 Readiness Assessment

> **Document type:** Certification (V1) · **Status:** Authoritative
> **Scoring:** see `V1_CERTIFICATION_STANDARD.md` §5

Scores each audit dimension with evidence. Scores reflect an **honest** audit: the
delivered offline pipeline is strong; dimensions that depend on provisional
foundations (the minimal `preprocessing`/`datasets`/`evaluation` integration
surfaces and synthetic data) are scored *Provisional/Adequate*, not *Strong*.

---

## Scores

| # | Dimension | Score | Band | Evidence / rationale |
|---|-----------|------:|------|----------------------|
| 1 | Architecture Readiness | 95 | Strong | Acyclic DAG enforced by `tests/test_boundaries.py` incl. `backend↛frontend`, `frontend↛domain`, `ml↛evaluation`. |
| 2 | Scientific Readiness | 80 | Adequate | Temperature scaling, split-conformal (marginal coverage), patient-disjoint metrics correctly applied; validated on **synthetic** data (no real EEG yet). |
| 3 | Evaluation Readiness | 88 | Adequate | Patient-disjoint enforced + audited; benchmarking refuses non-disjoint (NR-3). Evaluation module is a focused V1-P4 surface (see Gap Analysis). |
| 4 | Model Readiness | 90 | Strong | EEGNet/TCN/SimpleCNN train, predict, register, reproduce bit-for-bit; weights checksummed. |
| 5 | Calibration Readiness | 90 | Strong | Calibration + conformal + coverage produced and validated; coverage meets target on patient-disjoint test. |
| 6 | Application Readiness | 90 | Strong | Import-pure offline app; 5 workflows + 11 visualizations from registered artifacts; deterministic static HTML; app-consistency validation passes. |
| 7 | Governance Readiness | 78 | Adequate | Versioning/lineage/registries/decision-records operate and are tested; **`.gcc/` mechanized enforcement (V0-P3) is contract-only** — boundary enforcement currently lives in tests. |
| 8 | Repository Readiness | 92 | Strong | Pinned deps, deterministic artifacts, comprehensive test suite, clean layout, ignored run artifacts. |
| 9 | Version Readiness | 95 | Strong | No forbidden V2+ work; offline-only backend/frontend recorded in ADR-0002; scope discipline held. |

**Aggregate:** weighted toward delivered-scope strength; **no dimension < 50**.

## Interpretation

- The **offline platform** (models → uncertainty → inference → application) is
  **Strong** and fully verifiable.
- The lower-scored dimensions (Scientific, Evaluation, Governance) are limited by
  **provisional foundations**, not by defects in the V1-P7/P8 work:
  - synthetic-only data (Scientific),
  - minimal V1-P4 evaluation surface (Evaluation),
  - contract-only V0-P3 governance mechanization (Governance).

These are the basis for the **CERTIFIED (QUALIFIED)** verdict in the Completion
Report and the blockers in the V2 Readiness Gate.
