# `tools/` — Developer & Maintainer Tooling

> **Layer:** Cross-cutting support (outside the production dependency graph)
> **Directory README type:** Repository Architecture Foundation (V0-P2)
> **Status (V0):** Boundary contract defined; **no code yet** (correct for V0).
> **Governing docs:** AP-7 (boundaries), AP-11 (governance by construction), NR-8, [`../docs/architecture/IMPORT_RULES.md`](../docs/architecture/IMPORT_RULES.md)

Internal tooling that **supports** developers, reviewers, and the governance
layer — for example, utilities that check boundaries or generate documentation
artifacts. Tools are **never imported by production code.**

---

## Purpose
Provide internal, developer-facing utilities that improve maintainability,
enforce governance, and reduce manual effort — without becoming part of the
runtime platform.

## Responsibilities
- House utilities supporting **governance enforcement** (e.g. helpers used by the
  GCC import/boundary checks) and repository hygiene (AP-11).
- Provide documentation/diagram generation or consistency-checking helpers.
- Offer developer convenience utilities that respect all boundaries.

## Allowed dependencies
- ✅ May import platform modules **as needed for tooling purposes** (e.g. to
  analyze them), and pinned third-party tooling libraries.
- ✅ May read `docs/` and `.gcc/` definitions to perform checks.

## Forbidden dependencies
- ❌ Being imported **by** any production module (`preprocessing`, `datasets`,
  `ml`, `evaluation`, `backend`, `frontend`, `monitoring`, `deployment`) — tools
  are a leaf for production, never a dependency of it (NR-8).
- ❌ Becoming a backdoor that smuggles forbidden cross-module dependencies into
  production via "tooling."

## Future responsibilities
- **V0-P3+:** utilities backing GCC boundary/import checks and decision-record management.
- **V1+:** reproducibility/provenance helpers; data/catalog inspection tools.
- **V4:** operational tooling for hospital deployment support.

## Version ownership
- **Active from V0** (supports governance/consistency); grows across versions.
- Contract defined in **V0-P2** (this README).

## Examples
- A boundary-scan utility that lists imports per module for GCC to validate.
- A docs consistency checker that flags an undefined glossary term.
- A generator that renders the dependency graph from the documented rules.

## Boundary rules
- **Production code must never import `tools/`.** Tools support development and
  governance, not the running platform (see
  [`../docs/architecture/DEPENDENCY_GRAPH.md`](../docs/architecture/DEPENDENCY_GRAPH.md)).
- Tools must **not** be used to bypass import rules; they enforce them.
- Distinguished from `scripts/`: `tools/` are reusable utilities; `scripts/` are
  runnable operational procedures.
