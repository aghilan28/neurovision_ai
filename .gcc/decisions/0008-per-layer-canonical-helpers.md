# DR-0008 · Per-layer canonical/findings helpers (controlled duplication)

- **Status:** Accepted · **Phase:** V1-P3 / V1-P4 · **Date:** caller-supplied

## Context
`datasets`, `preprocessing`, and now `evaluation` each need small canonical-JSON /
hashing / fingerprint helpers, and a `Finding`/`Severity` value object. A single
shared module would reduce duplication but would be a **new architectural node**
(a shared leaf imported by multiple layers), which is a governance event under the
fixed dependency graph (NR-8) and not in V1-P3/P4 scope.

## Decision
- Each top-level layer keeps its **own** `_canonical.py` (canonical JSON, SHA-256,
  fingerprints) — three small copies — to preserve `preprocessing` as a pure leaf
  and keep each layer self-contained (extends DR-0003).
- **Within** `evaluation`, the `Finding`/`Severity` primitive lives once in
  `evaluation/_findings.py` and is re-exported by
  `evaluation.dataset_intelligence.schemas.common` (single source of truth inside
  the package). The shared evaluation-level provenance (`VersionBundle`) lives in
  `evaluation/_provenance.py`.

## Alternatives considered
1. **New shared `contracts/types` leaf module** imported by all layers — reduces
   duplication but changes the architecture; deferred to a governance decision (the
   dependency-graph doc already lists this as a *possible future* node).
2. **Reach into another layer's private `_canonical`** — couples layers to private
   symbols and (for preprocessing) would violate leaf purity. Rejected.

## Consequences
- A few dozen lines duplicated across layers; isolated, tested, and intentional.
- The acyclic dependency graph and `preprocessing` leaf purity are preserved
  (verified by boundary tests).

## Rules / principles invoked
AP-1 (no premature architecture change), AP-7/NR-8 (boundaries, acyclic graph),
NR-2 (recorded as *not* debt — see `.gcc/debt`).
