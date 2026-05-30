# Decision Records — Multi-Case Intelligence Layer (V2-P5)

Versioned, dated decision records (Rule **NR-5**, Principle **AP-9**). Dates are
recorded as the implementing phase rather than a wall-clock timestamp, to keep
the repository deterministic.

---

## DR-P5-1 — Intelligence lives as a `backend/` subsystem
**Decision.** Implement V2-P5 as `backend/multi_case_intelligence/`, a subsystem
of the Application Layer.
**Rationale.** Multi-case intelligence is orchestration over domain truth, which
is the Application Layer's role (AP-7). It preserves the uncertainty/provenance
flowing up from V1.
**Alternatives considered.** A new top-level layer (rejected: would change the
fixed seven-layer architecture, violating AP-1/NR-6).

## DR-P5-2 — Content-addressed identity, logical-clock ordering
**Decision.** All ids are content hashes; all ordering uses logical sequence
numbers. No `uuid`, `random`, or `datetime` is permitted.
**Rationale.** Determinism and reproducibility (AP-3/AP-6, NR-9/NR-10) are
cross-version invariants; wall-clock/random values would make artifacts
irreproducible and un-auditable.
**Alternatives.** UUID ids + timestamps (rejected: non-reproducible).

## DR-P5-3 — Logical id = definition, content hash = result
**Decision.** Artifact logical ids derive from the *definition/scope*; content
hashes derive from the *result*.
**Rationale.** Enables meaningful versioning: re-computing the same question over
evolved data produces a new version of the same logical artifact (auditable),
rather than a brand-new unrelated artifact.
**Alternatives.** Id = full content (rejected: every data change creates an
orphan artifact and version history is lost).

## DR-P5-4 — Explicit, minimal source integration port
**Decision.** Model upstream V0/V1/V2 artifacts as immutable dataclasses in
`schemas/source.py` rather than importing not-yet-materialized modules.
**Rationale.** "No isolated implementation" requires defined integration
contracts; an explicit port is the honest, testable seam. The field set is a
faithful subset of the documented contracts (incl. V1 `UncertaintySignal`).
**Alternatives.** Stub/`Any` inputs (rejected: untyped, untestable, unsafe);
inventing the upstream modules wholesale (rejected: out of phase scope, NR-13).

## DR-P5-5 — Registry-mediated admission with mandatory gate
**Decision.** No artifact is usable until it passes the `GovernanceGate` and is
admitted to the `IntelligenceRegistry`, which writes an immutable audit event and
a lineage record.
**Rationale.** Mechanizes "no artifact outside registry" and governance-by-
construction (AP-8/AP-11, NR-11). 
**Alternatives.** Optional/after-the-fact registration (rejected: allows
ungoverned artifacts).

## DR-P5-6 — Trends over a logical ordinal dimension
**Decision.** Trends are computed over the sorted distinct case `ordinal` values
supplied by the upstream case layer, not over timestamps.
**Rationale.** Keeps trend analysis deterministic and free of wall-clock
dependence while still expressing temporal-style ordering.
**Alternatives.** Timestamp bucketing (rejected: non-deterministic, NR-9).
