# `frontend/` — Presentation Layer

> **Layer:** Presentation Layer
> **Directory README type:** Repository Architecture Foundation (V0-P2)
> **Status (V0):** Boundary contract defined.
> **Status (V1-P8):** **Offline implementation present** — `offline_research_app/` (presentation-only; imports no domain module). Clinical UI remains V2+.
> **Governing docs:** AP-4 (faithful uncertainty), AP-7 (boundaries), NR-4, NR-8, [`../docs/architecture/IMPORT_RULES.md`](../docs/architecture/IMPORT_RULES.md)

The clinician-facing layer. Its single hard constraint defines the platform's
strictest boundary: **the frontend may not import any domain module.** It speaks
to the rest of the system **only through the backend API.**

---

## Purpose
Present detections, the IIC, and their **uncertainty** to clinicians in a way that
supports review, triage, and trust — without ever touching domain code directly.

## Responsibilities
- Render detections and IIC characterization for clinician review (V2+).
- **Faithfully communicate uncertainty** — never hide, flatten, or distort it
  (AP-4, NR-4).
- Support triage/prioritization workflows.
- Consume the backend's API contracts; surface provenance/audit references so
  clinicians can trace what they see.

## Allowed dependencies
- ✅ The **backend API** (over the network, via defined contracts) — **only**.
- ✅ Pinned third-party UI libraries.

## Forbidden dependencies
- ❌ `backend/` **as a code import**, and ❌ `ml/`, ❌ `preprocessing/`,
  ❌ `datasets/`, ❌ `evaluation/` — the frontend imports **none** of these (NR-8).
  This is the canonical forbidden-import example in
  [`../docs/architecture/IMPORT_RULES.md`](../docs/architecture/IMPORT_RULES.md).
- ❌ `monitoring/`, `deployment/` as code imports.
- ❌ Presenting clinical results **without** their uncertainty (NR-4).

## Future responsibilities
- **V2:** the clinical review/triage interface with faithful uncertainty rendering.
- **V3:** near-real-time monitoring views.
- **V4:** hospital-deployment-ready UI (security, accessibility, reliability).

## Version ownership
- **Introduced/owned from V2.** Contract defined in **V0-P2** (this README).

## Examples
- A review screen showing a detection with its conformal prediction set and a
  clear "uncertain — needs review" state.
- A prioritized worklist ordered by clinical urgency and model confidence.
- A trace/"why" panel linking a displayed result to its provenance via the API.

## Boundary rules
- **Imports no domain module.** All data arrives via the backend API
  (see the acyclic [dependency graph](../docs/architecture/DEPENDENCY_GRAPH.md)).
- Must render uncertainty faithfully; a UI that drops uncertainty violates NR-4.
- Contains **no** DSP, modeling, evaluation, or data-curation logic — those live
  behind the backend.
- The frontend↔backend boundary (API-only) is a **V2 exit criterion**.


---

## V1 Offline Implementation (V1-P8)

> A **governed scope extension** (offline presentation layer in V1). Decision:
> [`../.gcc/decisions/ADR-0002`](../.gcc/decisions/ADR-0002-v1-p7-p8-offline-inference-and-research-app.md).

`frontend/offline_research_app/` is the **Offline Research Application** — a
presentation-only workstation that reads the backend's **registered artifacts**
(JSON) and renders them as view-models + a static, offline HTML report (CSS-only
tabs, inline SVG, no JavaScript, no external assets).

- **Strictest boundary upheld.** Imports **no** domain module (not even `backend`
  as code) — standard library only. The offline frontend↔backend boundary is a
  data/file boundary (read registered artifacts), stricter than the V2 API
  boundary. Enforced by `tests/test_boundaries.py`.
- **Faithful uncertainty (NR-4).** Calibration, conformal sets, coverage, and risk
  are always shown alongside predictions; nothing is flattened to a bare label.
- **Five workflows** (Upload, Dataset Intelligence, Inference, Benchmark, Audit) and
  **eleven visualizations**, all sourced from registered artifacts.

See [`offline_research_app/README.md`](./offline_research_app/README.md).
