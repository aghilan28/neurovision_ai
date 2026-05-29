# V1 Gap Analysis

> **Document type:** Certification (V1) · **Status:** Authoritative
> **Purpose:** name the difference between the **delivered** V1 and an
> **unqualified-CERTIFIED** V1, with severity and remediation. No gap is hidden (NR-2).

---

## Gap register

| ID | Gap | Severity | Impact | Remediation |
|----|-----|:--------:|--------|-------------|
| G1 | **Synthetic data only.** The pipeline runs on a deterministic synthetic cEEG source; no real patient EEG ingested/validated. | High (for clinical claims) / Low (for offline pipeline proof) | Scientific generalization is unproven; metrics are not clinically meaningful. | Land a real-EEG dataset adapter behind the existing `EEGDataset` contract; re-run patient-disjoint evaluation + domain-shift (held-out site/montage). |
| G2 | **Minimal V1-P1/P2/P3 foundations.** `preprocessing`/`datasets` implement focused integration surfaces, not the full authoritative phases. | Medium | Some real-world DSP/curation/intelligence capabilities are not present. | Extend (not rewrite) behind current contracts when the authoritative phases land (ADR-0001 D1). |
| G3 | **Minimal V1-P4 evaluation surface.** Evaluation covers patient-disjoint metrics + calibration/coverage; broader domain-shift batteries are limited. | Medium | Shift-aware generalization claims (NR-15) are not yet fully exercised. | Expand evaluation harness (held-out-site/montage suites) and wire into benchmarking. |
| G4 | **V0-P3 governance not mechanized.** `.gcc/` boundary/quality enforcement is contract-only; enforcement currently lives in `tests/`. | Medium | Governance relies on the test suite + review rather than a standalone GCC gate. | Implement `.gcc/` mechanized checks (import-rule scanner, debt registry, version gates) as the V0-P3 deliverable. |
| G5 | **Offline ingestion is config-driven, not file-upload.** "Upload" is modeled as a processed run; there is no real EEG file parser. | Low (V1 scope) | The app's upload workflow displays registered intelligence rather than parsing an uploaded binary. | Add a real EEG file reader (e.g. EDF) in the data layer behind `EEGDataset`. |
| G6 | **Backend/Frontend introduced early.** Architecture marks these V2; V1-P7/P8 introduces *offline-only* versions. | Low | Intentional, governed scope extension. | Recorded + bounded in ADR-0002; hardening deferred to V2+. |

## What is NOT a gap (delivered and verified)

- End-to-end offline inference with full traceability (15 stages).
- Deterministic reproducibility (content-addressed ids; identical checksums).
- Patient-disjoint enforcement + benchmark refusal of leakage (NR-3).
- Calibration + conformal + coverage + risk, validated.
- Import-pure offline application reading only registered artifacts.
- Acyclic boundaries enforced by tests, including the new backend/frontend edges.

## Closure criteria for unqualified CERTIFIED

V1 reaches unqualified **CERTIFIED** when **G1–G4** are closed (real EEG validated;
authoritative V1-P1…P4 landed; V0-P3 governance mechanized) with all tests and
verification scripts still green.
