# V1 Risk Review

> **Document type:** Certification (V1) · **Status:** Authoritative
> **Realizes:** AP-10 (domain shift), NR-2 (debt visible), NR-15 (no overclaiming generalization)

Open risks for Version 1, with likelihood/impact and mitigation. Risks are stated
honestly; none is downgraded to ease certification.

---

## Risk register

| ID | Risk | Likelihood | Impact | Mitigation / status |
|----|------|:----------:|:------:|---------------------|
| R1 | **Synthetic→real gap.** Methods that work on synthetic cEEG may not transfer to real EEG (artifacts, montages, class imbalance). | High | High | Real-EEG validation is a **V2 blocker**; no clinical claim is made in V1 (Scope/NR-15). |
| R2 | **Calibration drift under shift.** Temperature + conformal calibrated on one distribution may degrade under site/montage shift. | Medium | High | Coverage is *measured*, not assumed; AP-10/NR-15 require shift-aware eval before any generalization claim. |
| R3 | **Conformal exchangeability.** The coverage guarantee assumes exchangeability between calibration and test; real cross-patient shift can weaken it. | Medium | Medium | Calibration/test are patient-disjoint; coverage drift is tracked and reported per run. |
| R4 | **Governance not yet mechanized (V0-P3).** Boundary enforcement depends on the test suite; a bypassed test could admit drift. | Medium | Medium | `tests/test_boundaries.py` runs in the suite; mechanize `.gcc/` gate (G4) to remove reliance on test discipline alone. |
| R5 | **Provisional foundations diverge.** When authoritative V1-P1…P4 land, contracts could drift from these minimal foundations. | Medium | Medium | Contracts are explicit + versioned; reconcile by extension (ADR-0001 D1) and re-run the audit. |
| R6 | **Determinism dependence on pinned NumPy.** Reproducibility is guaranteed under the pinned environment; an unpinned upgrade could change bytes. | Low | Medium | `requirements.txt`/`pyproject.toml` pin exact versions; manifests record environment. |
| R7 | **Scope creep toward V2.** Pressure to add APIs/real-time/clinical UI. | Low | Medium | Forbidden-work list honored; offline-only recorded in ADR-0002; V2 gate is explicit. |
| R8 | **Class/label realism.** Synthetic class morphology is a stylized proxy for ACNS IIC patterns. | High | Low (V1) | Documented; superseded once real labels are ingested (R1). |

## Residual risk statement

For the **delivered offline scope**, residual risk is **low**: the platform is
deterministic, patient-disjoint, uncertainty-aware, and fully audited. For any
**clinical or generalization** interpretation, residual risk is **high and
unaccepted** — explicitly out of V1 scope and gated behind V2 (R1, R2).
