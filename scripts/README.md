# `scripts/` — Operational & Automation Scripts

> **Layer:** Cross-cutting support (outside the production dependency graph)
> **Directory README type:** Repository Architecture Foundation (V0-P2)
> **Status (V0):** Boundary contract defined; **no code yet** (correct for V0).
> **Governing docs:** AP-6 (reproducibility), AP-9 (versioned decisions), NR-8, NR-10, [`../docs/architecture/IMPORT_RULES.md`](../docs/architecture/IMPORT_RULES.md)

Runnable procedures that **drive** the platform's modules for repeatable
operational tasks (e.g. "run the evaluation harness," "regenerate a result").
Scripts compose modules; production modules never import scripts.

---

## Purpose
Provide thin, **reproducible** entry points that orchestrate modules for
operational and developer workflows, leaving the heavy logic inside the modules
themselves.

## Responsibilities
- Offer runnable procedures (e.g. run training/evaluation, regenerate a reported
  result, perform a one-off maintenance task).
- Keep procedures **reproducible**: pinned inputs, recorded parameters/provenance
  (AP-6, NR-10).
- Stay **thin** — orchestrate module APIs rather than re-implement logic.

## Allowed dependencies
- ✅ May invoke/import platform modules to orchestrate them (e.g. call `evaluation/`
  via its public interface).
- ✅ Pinned third-party CLI/automation libraries.

## Forbidden dependencies
- ❌ Being imported **by** any production module (NR-8) — scripts are top-level
  entry points, not library dependencies.
- ❌ Embedding domain logic that belongs in a module (it would escape testing,
  boundaries, and governance).
- ❌ Producing irreproducible artifacts on the reported path (NR-10).

## Future responsibilities
- **V1:** scripts to run the deterministic pipeline and the patient-disjoint
  evaluation, reproducibly.
- **V3:** scripts supporting near-real-time operation.
- **V4:** operational/maintenance scripts for hospital deployment.

## Version ownership
- **Active from V0** (consistency/governance automation); grows across versions.
- Contract defined in **V0-P2** (this README).

## Examples
- A script that runs the LOSO evaluation end-to-end and writes a provenance-tagged report.
- A script that regenerates a previously reported result from pinned inputs/code.
- A maintenance script that validates documentation consistency in CI.

## Boundary rules
- **Production code must never import `scripts/`** (see
  [`../docs/architecture/DEPENDENCY_GRAPH.md`](../docs/architecture/DEPENDENCY_GRAPH.md)).
- Scripts must respect every import rule of the modules they orchestrate; they may
  not be used to cross forbidden boundaries.
- Distinguished from `tools/`: `scripts/` are runnable procedures; `tools/` are
  reusable utilities.
