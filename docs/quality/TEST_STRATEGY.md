# TEST STRATEGY

> **Document type:** Quality Assurance Foundation (V0-P5) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Quality Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Policy authority:** [`../governance/Testing_Governance.md`](../governance/Testing_Governance.md) (this document **elaborates** it; on conflict, Testing Governance governs).
> **Feeds:** the **Testing Gate (G4)** in [`QUALITY_GATES.md`](./QUALITY_GATES.md)

This is the complete **testing philosophy and strategy** for V1 → V4. Testing
Governance (V0-P3) is the *policy* (what must be tested, gating, thresholds); this
document is the *strategy* (which test types exist, when each is **required** vs.
**forbidden**, ownership, minimum requirements, and how the suite expands by risk).
They are consistent by construction; this document never weakens a Testing
Governance rule.

> **Premise (inherited):** tests are how invariants become executable. *A guarantee
> that is not tested is a guarantee that will silently break.* V0 has no code, so
> V0 "testing" = documentation/consistency validation
> ([`../governance/Documentation_Governance.md`](../governance/Documentation_Governance.md) §8).

---

## 1. Strategy Principles
1. **Test invariants first.** Every cross-version invariant has a guarding test
   (Testing_Governance §1).
2. **Risk-based depth.** Test effort scales with blast radius and clinical
   relevance, not uniformly (§5).
3. **Determinism throughout.** Tests are deterministic; flaky guarding tests are
   defects (AP-3 spirit).
4. **Tests live with code.** Behavior changes update tests in the same change set.
5. **Never weaken a test to pass** (NR-2). A guarding test failing is
   stop-and-remediate.
6. **`tests/` is the only all-importer.** It may import any module; production
   never imports `tests/` ([`../architecture/IMPORT_RULES.md`](../architecture/IMPORT_RULES.md)).

## 2. Test Types — required, forbidden, ownership, minimum

For each type: **When required · When forbidden · Owner · Minimum requirement.**
(Types 2.1–2.5 expand Testing_Governance §2; 2.6–2.10 are the strategy's forward
plan.)

### 2.1 Unit Tests
- **Required:** for every public function/unit in a domain module (V1+).
- **Forbidden:** as a substitute for contract/integration tests across boundaries;
  unit tests must not reach across modules.
- **Owner:** the module's implementer. **Minimum:** normal + boundary + failure
  inputs; preprocessing units **must** include a determinism test (NR-9).

### 2.2 Integration Tests
- **Required:** for every exercised **allowed** dependency edge (e.g.
  `datasets → preprocessing`, `ml → datasets`).
- **Forbidden:** exercising any **forbidden** edge (would itself be NR-8 drift).
- **Owner:** implementer of the higher module. **Minimum:** provenance preserved
  across the chain; realistic controlled fixtures.

### 2.3 Contract Tests
- **Required:** for every public inter-module contract — **especially the backend↔
  frontend API and the uncertainty+provenance payload** (V2+).
- **Forbidden:** changing a contract test before its contract change has an ADR.
- **Owner:** the contract's producer. **Minimum:** assert shape **and** that
  uncertainty + provenance are present and unaltered across the boundary (NR-4/NR-11).

### 2.4 Architecture Tests
- **Required:** always (V0 consistency checks; V1+ executable).
- **Forbidden:** never — these complement GCC and may not be disabled.
- **Owner:** Founder (Quality Owner). **Minimum:** assert acyclic graph; `frontend`
  imports no domain module; `preprocessing` imports nobody; no import rule broken.

### 2.5 System Tests (end-to-end)
- **Required:** for end-to-end flows once multiple layers exist (V2+: raw → preproc
  → ml → backend → frontend), asserting **end-to-end traceability**.
- **Forbidden:** as a replacement for unit/contract coverage of the parts.
- **Owner:** Founder. **Minimum:** a representative path produces a traceable,
  uncertainty-bearing output (NR-11/NR-4).

### 2.6 Performance Tests
- **Required:** when a latency/throughput target exists (V3+ streaming).
- **Forbidden:** trading determinism or correctness for performance without an ADR;
  performance tests never justify weakening an invariant.
- **Owner:** Founder. **Minimum:** measured against a **recorded** target; results reproducible.

### 2.7 ML Tests
- **Required:** for any model/inference path (V1+): reproducibility, calibration/
  coverage, robustness (held-out site/montage), abstention, no-leakage.
- **Forbidden:** reporting any model metric on a **non-patient-disjoint** split
  (NR-3); presenting in-distribution-only numbers as general (NR-15).
- **Owner:** ML implementer + Founder. **Minimum:** patient-disjoint evaluation;
  measured calibration + conformal coverage; abstention on ambiguous input (AP-4).

### 2.8 Clinical Validation Tests
- **Required:** for any clinically meaningful claim (V1+): the VC-CLIN evidence set
  ([`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md) §9).
- **Forbidden:** emitting a clinical output **without** calibrated uncertainty
  (NR-4) or **without** traceability (NR-11); these are never waivable (G5).
- **Owner:** Founder (Quality Owner). **Minimum:** patient-disjoint + calibration/
  coverage + domain-shift delta + abstention behavior, all reproducible.
> *Engineering* validation of clinical-relevance properties — **not** a regulatory process.

### 2.9 Monitoring Tests
- **Required:** for observability/drift logic (V3+): drift detectors fire on
  injected shift; alert thresholds (recorded) behave as specified.
- **Forbidden:** shipping monitoring whose detectors are untested ("we'll trust it").
- **Owner:** Founder. **Minimum:** drift-detection test on synthetic shift; alert path tested.

### 2.10 Future Streaming Tests
- **Required:** for near-real-time ingestion/inference (V3+): streaming correctness;
  **no cross-patient leakage** introduced by windowing/buffering (NR-3); regression
  that V1/V2 guarantees hold under streaming.
- **Forbidden:** any streaming design that leaks across patients or breaks determinism without an ADR.
- **Owner:** Founder. **Minimum:** leakage-free windowing test; V1/V2 regression suite green under streaming.

## 3. Required Tests by Version (inherited from Testing_Governance §3)
| Version | Must be validated |
|---------|-------------------|
| **V0** | Documentation/consistency (orphans, conflicts, links, terms, ownership). |
| **V1** | Preprocessing determinism; patient-disjoint evaluation; calibration/coverage; reproducibility; boundary/acyclicity. |
| **V2** | API contract incl. uncertainty/provenance; end-to-end traceability; frontend imports no domain module; **no V1 regression**. |
| **V3** | Streaming correctness; latency/reliability; drift detection; **no V1/V2 regression**. |
| **V4** | Full regression across V1–V3; reliability/load; security/operational; audit-trail completeness. |

## 4. Minimum Requirements (the floor, every version)
- 100% of **invariant behaviors** tested (no acceptable gap) — Testing_Governance §4.
- Architecture tests present and green (acyclicity + boundaries).
- Zero disabled guarding tests; zero flaky guarding tests.
- Every public contract has a contract test (once the contract exists).
- Every reported result reproducible (NR-10).

## 5. Risk-Based Expansion Strategy
Start at the floor (§4) and expand depth by risk tier and clinical relevance:
- **A1/Minor, low clinical relevance:** unit + relevant integration.
- **A2/Major (new contract/dependency):** + contract tests + the new edge's integration.
- **A3/Architecture:** + architecture tests + full invariant regression + system test of affected path.
- **Clinical-relevant paths:** + ML/clinical validation tests (always, regardless of tier).
- **Streaming/load paths (V3+):** + performance/monitoring/streaming tests.

Expansion is **recorded**: when a class of defect is found, add a guarding test so
it cannot recur (corrective→preventive, [`FAILURE_HANDLING.md`](./FAILURE_HANDLING.md)).

## 6. Failure & Gating (inherited)
- Failing invariant/architecture/contract test = build red = no merge/release
  (Testing_Governance §5–§6, Testing Gate G4).
- A genuinely wrong test is fixed via a **recorded** change explaining why.
- Coverage *number* may be a per-version release gate, but **invariant coverage is
  non-negotiable** regardless of the number.

## 7. Relationship To Other Documents
- Policy: [`../governance/Testing_Governance.md`](../governance/Testing_Governance.md) · Gates: [`QUALITY_GATES.md`](./QUALITY_GATES.md)
- Validation taxonomy: [`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md) · Module contract: [`../../tests/README.md`](../../tests/README.md)

Changes to this document are governance-class and require an ADR.
