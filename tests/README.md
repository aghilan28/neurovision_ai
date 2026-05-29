# `tests/` — Cross-Cutting Test Suite

> **Layer:** Cross-cutting (test-only; outside the production dependency graph)
> **Directory README type:** Repository Architecture Foundation (V0-P2)
> **Status (V0):** Boundary contract defined; **no code yet** (correct for V0).
> **Governing docs:** AP-2/AP-3/AP-6 (validation foundations), NR-3/NR-9/NR-10, [`../docs/architecture/IMPORT_RULES.md`](../docs/architecture/IMPORT_RULES.md)

The one place permitted to import **everything** — because its job is to verify
that everyone else obeys the rules. Tests are **test-only**: production code never
imports them.

---

## Purpose
Verify correctness, determinism, reproducibility, boundary integrity, and (from
V1) the platform's clinical guarantees — and **fail the build** when a rule is
violated.

## Responsibilities
- Unit/integration/end-to-end tests across all modules.
- **Determinism tests** for `preprocessing/` (AP-3, NR-9).
- **Patient-disjointness tests** asserting splits never share a patient (AP-2, NR-3).
- **Reproducibility checks** that reported results regenerate (AP-6, NR-10).
- **Boundary/import tests** proving forbidden imports do not exist (e.g. that
  `frontend/` imports no domain module) — complementary to GCC checks (AP-7, NR-8).
- **Traceability tests** that clinical outputs carry full provenance (AP-5, NR-11).

## Allowed dependencies
- ✅ **Any** module in the repository (`preprocessing`, `datasets`, `ml`,
  `evaluation`, `backend`, `frontend`, `monitoring`, `deployment`, `tools`).
- ✅ Pinned third-party test frameworks/fixtures.

## Forbidden dependencies
- ❌ Being imported **by** any production module — tests are a sink, never a source
  of production dependencies.
- ❌ Introducing nondeterminism that would make tests flaky/irreproducible.

## Future responsibilities
- **V1:** determinism, patient-disjoint, reproducibility, and boundary test suites.
- **V2:** API contract + end-to-end traceability tests.
- **V3:** streaming-correctness, latency/load, and drift-detection tests.
- **V4:** full regression suite across all prior-version guarantees + reliability tests.

## Version ownership
- **Active from V0** (documentation/consistency checks) and grows every version.
- Contract defined in **V0-P2** (this README).

## Examples
- A test asserting a preprocessing transform is byte-identical across runs.
- A test that fails if any patient ID appears in both train and test partitions.
- A boundary test that scans `frontend/` and fails on any forbidden domain import.

## Boundary rules
- May import any module; is **never** imported by production code (so it stays
  outside the acyclic production
  [dependency graph](../docs/architecture/DEPENDENCY_GRAPH.md)).
- Tests **encode the rules as executable checks**; a failing guarantee test is a
  failing build, not a warning.
- Tests do not relax guarantees to pass — a guarantee that cannot be met is a
  stop-and-remediate event, not a reason to weaken the test.
