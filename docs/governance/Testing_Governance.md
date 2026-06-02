# TESTING GOVERNANCE

> **Document type:** Governance Layer (V0-P3)
> **Status:** Authoritative
> **Owner:** Founder (Quality Owner role)
> **Update procedure:** Governance-class change (ADR). Concrete test *suites* are added per version under this policy.
> **Enforces:** Principles **AP-2, AP-3, AP-6, AP-7, AP-10, AP-11** and Rules **NR-3, NR-8, NR-9, NR-10, NR-11, NR-15**
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

This document governs testing for **Version 1 through Version 4**. V0 has no
executable code, so V0 "testing" is **documentation/consistency validation**
(orphans, conflicts, links, terms, ownership — see
[`Documentation_Governance.md`](./Documentation_Governance.md) §8). From V1
onward, this document is the authority on what must be tested, to what standard,
and how testing gates releases.

> **Premise:** tests are how the project's **invariants become executable.** A
> guarantee that is not tested is a guarantee that will silently break. Testing is
> a clinical-safety property, not a chore.

---

## 1. Testing Philosophy

1. **Invariants are tests.** Every cross-version invariant
   ([`../VERSION_EVOLUTION_MODEL.md`](../VERSION_EVOLUTION_MODEL.md) §6) has a
   corresponding test that fails the build if the invariant is violated.
2. **Patient-disjoint or it didn't happen.** Evaluation tests assert
   patient-disjoint splits (AP-2, NR-3); a leaked split is a build failure.
3. **Determinism is testable.** Preprocessing tests assert identical output for
   identical input + version (AP-3, NR-9).
4. **Boundaries are testable.** Tests assert no forbidden import / no cycle
   (AP-7, NR-8), complementing GCC checks.
5. **Tests never relax to pass.** If a guarantee can't be met, that is
   stop-and-remediate — never weaken the test.
6. **Reproducible tests.** Tests are deterministic; flaky tests are defects, not
   noise.
7. **Test ownership lives with the code.** A change that alters behavior updates
   its tests in the same change set.

The `tests/` module is the only one allowed to import every module
([`../architecture/IMPORT_RULES.md`](../architecture/IMPORT_RULES.md)); production
code never imports `tests/`.

## 2. Test Categories & Standards

### 2.1 Unit Testing
- **Scope:** a single function/unit within one module.
- **Standard:** deterministic; no hidden I/O; fast; covers normal, boundary, and
  failure inputs. Preprocessing units **must** include a determinism test.

### 2.2 Integration Testing
- **Scope:** interactions across modules along an allowed dependency edge (e.g.
  `datasets → preprocessing`, `ml → datasets`).
- **Standard:** uses realistic but controlled fixtures; preserves provenance
  through the chain; no forbidden edges exercised.

### 2.3 Contract Testing
- **Scope:** the public contracts between modules — especially the **backend↔
  frontend API** and the **uncertainty + provenance payload**.
- **Standard:** asserts the contract shape and that **uncertainty and provenance
  are present and unaltered** across the boundary (AP-4/AP-5, NR-4/NR-11). A
  contract change requires an ADR before the test changes.

### 2.4 Architecture Testing
- **Scope:** structural invariants.
- **Standard (executable):** assert the dependency graph is **acyclic**; assert
  `frontend` imports no domain module; assert `preprocessing` imports nobody;
  assert no rule from [`../architecture/IMPORT_RULES.md`](../architecture/IMPORT_RULES.md)
  is broken. These complement (do not replace) GCC checks.

### 2.5 Validation/Evaluation Testing (the clinical-rigor tier)
- **Scope:** the `evaluation/` harness itself and the metrics it produces.
- **Standard:** assert **patient-disjoint** splits by construction (no patient in
  two partitions); assert calibration/coverage are computed; assert
  **held-out-site/montage** (domain-shift) evaluation is run for any
  generalization claim (AP-10, NR-15); assert results are reproducible (NR-10).

### 2.6 Future ML Testing (V1+ as models appear)
- **Reproducibility tests:** a reported result regenerates from pinned inputs/code.
- **Calibration/coverage tests:** stated confidence matches realized accuracy;
  conformal coverage meets target error rate.
- **Robustness tests:** performance under held-out sites/montages reported as a
  delta, not hidden.
- **Abstention tests:** the model abstains/escalates on genuinely ambiguous input
  rather than forcing a low-confidence answer (AP-4).
- **No-leakage tests:** windowing/augmentation/streaming never lets a patient span
  splits (NR-3) — especially important when V3 streaming is added.

### 2.7 Future Real-Time/Reliability Testing (V3+)
- Streaming-correctness, latency/load, and drift-detection tests; regression tests
  asserting V1/V2 guarantees still hold under streaming.

## 3. Validation Requirements (per version)

| Version | Must be validated |
|---------|-------------------|
| **V0** | Documentation consistency (orphans, conflicts, links, terms, ownership). |
| **V1** | Preprocessing determinism; patient-disjoint evaluation; calibration/coverage; reproducibility; boundary/acyclicity. |
| **V2** | API contract incl. uncertainty/provenance; end-to-end traceability; frontend imports no domain module; **no V1 regression**. |
| **V3** | Streaming correctness; latency/reliability targets; drift detection; **no V1/V2 regression**. |
| **V4** | Full regression across V1–V3; reliability/load; security/operational; audit-trail completeness. |

## 4. Coverage Expectations

Coverage is **risk-weighted**, not a single global percentage:
- **Invariant-critical paths** (preprocessing determinism, split disjointness,
  uncertainty/provenance propagation, import boundaries): **100% of the invariant
  behaviors are tested** — these have no acceptable gap.
- **Core domain logic** (`ml`, `evaluation`, `datasets`, `preprocessing`, `backend`):
  high coverage; every public contract tested.
- **Presentation/infra:** behavior- and contract-focused coverage.

A coverage *number* may be set per version as a release gate, but coverage **of
invariants is non-negotiable regardless of the number**.

## 5. Failure Handling

- A failing **invariant/architecture/contract** test = **stop-and-remediate**;
  the build is red; no merge, no release.
- A failing test is **never disabled to go green**; disabling a guarding test is a
  governance violation (it hides debt — NR-2).
- A genuinely incorrect test is fixed via a recorded change explaining why.
- Flaky tests are treated as defects and fixed (determinism, AP-3 spirit).

## 6. Release Gating

A release ([`Release_Governance.md`](./Release_Governance.md)) is **blocked**
unless:
- [ ] All invariant/architecture/contract tests pass.
- [ ] The version's required validations (§3) pass.
- [ ] No guarding test is disabled.
- [ ] No prior-version guarantee has regressed.
- [ ] GCC checks pass (boundaries/imports/decisions).

## 7. Quality Thresholds

| Dimension | Threshold |
|-----------|-----------|
| Invariant coverage | 100% of invariant behaviors tested. |
| Build state for merge/release | Green; zero failing guarding tests. |
| Flakiness | Zero tolerated in guarding tests. |
| Reproducibility | Reported results regenerate within documented determinism tolerance. |
| Regression | Zero accepted in cross-version invariants. |

## 8. Relationship To Other Governance Documents
- Releases: [`Release_Governance.md`](./Release_Governance.md) · Reviews: [`Review_Governance.md`](./Review_Governance.md)
- Risk: [`Risk_Governance.md`](./Risk_Governance.md) · Architecture: [`Architecture_Governance.md`](./Architecture_Governance.md)
- Module contract: [`../../tests/README.md`](../../tests/README.md) · Mechanization: [`../../.gcc/README.md`](../../.gcc/README.md)

Changes to this document are governance-class and require an ADR.
