# V2 Risk Review

> **Document type:** Certification (V2) · **Status:** Authoritative
> **Realizes:** AP-10 (domain shift), NR-2 (debt visible), NR-15 (no overclaiming generalization)

Open risks for Version 2, with likelihood/impact and mitigation. Risks are stated
honestly; none is downgraded to ease certification. Risks are classified as
**Open**, **Resolved**, **Unknown** (monitored), or **Future** (V3+).

---

## Risk register

| ID | Risk | Class | Likelihood | Impact | Mitigation / status |
|----|------|:-----:|:----------:|:------:|---------------------|
| R1 | **Synthetic→real gap (inherited).** Clinical-workflow semantics are exercised on synthetic EEG-derived inputs; real-EEG behavior is unproven. | Open | High | High | Inherited V1 blocker; **no clinical claim** is made (Scope/NR-15). Closes with real-EEG validation. |
| R2 | **Decision-support over-reliance.** A reviewer could treat prioritization/guidance as a decision rather than support. | Open | Medium | High | Scope guard blocks diagnosis/treatment language; every record carries the explicit "clinician remains the decision-maker" statement; guidance is process-only. |
| R3 | **Governance not yet mechanized (V0-P3).** Boundary/quality enforcement depends on the test suite; a bypassed test could admit drift. | Open | Medium | Medium | `tests/test_boundaries.py` runs in the suite; mechanize `.gcc/` gate (V1 Gap G4 / V3 blocker). |
| R4 | **In-memory persistence.** Clinical/intelligence/decision state lives in-memory; the workstation reads a serialized snapshot, but there is no durable, checksummed store for the V2 subsystems. | Open | Medium | Medium | Snapshot is deterministic + reproducible; durable on-disk store (the V1 artifact-store pattern) is recorded remediation. |
| R5 | **Workstation/snapshot staleness.** The workstation renders a point-in-time snapshot; if the backend evolves, the snapshot must be rebuilt. | Open | Low | Low | Snapshot carries versions + integrity digest; rebuild is one command; staleness is visible in the meta block. |
| R6 | **Knowledge realism.** Seeded default knowledge is a stylized ACNS-aligned proxy, not a curated clinical ontology. | Open | Medium | Low (V2) | Documented; superseded by a curated terminology once real clinical knowledge is ingested. |
| R7 | **Cohort/population determinism vs. wall-clock.** Trends use a deterministic ordinal dimension, not real time; population stats are over a fixed snapshot. | Resolved | — | — | By design (no wall-clock); verified by reproducibility tests. |
| R8 | **Scope creep toward V3.** Pressure to add FHIR/EMR/real-time/streaming/deployment. | Future | Low | Medium | Forbidden-work list honored; recorded in ADR-0006; V3 gate is explicit. |
| R9 | **Determinism dependence on pinned NumPy (inherited).** Reproducibility holds under the pinned environment. | Open | Low | Medium | Dependency pinned; manifests/snapshots record environment. |
| RU1 | **Unknown real-world workflow fit.** How the workstation maps to a real reviewer's day is unvalidated (no users yet). | Unknown | — | — | Monitored; user validation is a V3+ concern. |

## Residual risk statement

For the **delivered offline clinical-workflow scope**, residual risk is **low**:
the platform is deterministic, fully audited, lineage-complete to the patient
root, decision-support-only, and presentation-pure. For any **clinical or
generalization** interpretation, residual risk is **high and unaccepted** —
explicitly out of V2 scope and gated behind V3 (R1, R2).
