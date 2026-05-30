# `frontend/clinical_workstation/` — Clinical Workstation (V2-P7)

> **Layer:** Presentation (`frontend/`) — imports **no** domain module (NR-8)
> **Status:** Implemented (V2-P7)
> **Governing docs:** AP-5/AP-8 (traceability/audit), AP-6 (reproducibility),
> AP-7/NR-8 (boundaries), AP-9 (versioned decisions);
> [`../../docs/architecture/IMPORT_RULES.md`](../../docs/architecture/IMPORT_RULES.md), ADR-0006

The first **unified workflow application** — the primary operational interface
over every Version 2 subsystem. A clinician/operator navigates
**Patient → Case → Study → Review → Finding → Interpretation → Knowledge →
Multi-Case Intelligence → Decision Support**, plus unified **Audit**, **Lineage**,
and **Reporting**, through one coherent environment.

---

## It is a presentation layer, not a source of truth
Everything displayed originates from **registered artifacts**: registries,
registered reports, immutable audit logs, the shared lineage graph, and recorded
validation results. The workstation **creates no hidden state** — the only state
it tracks is *deterministic navigation context* (current patient/case/review/…).

## The boundary (NR-8) and how it is honored
`frontend/` may import **nothing internal** (the strictest rule, enforced by
`tests/test_boundaries.py::test_frontend_imports_no_domain_module`). So the
workstation never imports `backend`/`ml`/etc. Instead:

1. **`scripts/build_workstation_snapshot.py`** (which *may* import backend)
   composes the real V2 services over **one shared lineage tracker**, runs a
   small deterministic multi-case workflow, and serializes every registered
   artifact into a single JSON **snapshot**.
2. **The workstation** reads that snapshot with stdlib `json` only and renders it.

```
backend services ──(scripts.build_workstation_snapshot)──▶ snapshot.json ──▶ frontend.clinical_workstation
        (source of truth)                                   (registered          (presentation only,
                                                              artifacts)           stdlib json only)
```

## Architecture (the seven workstation layers)
| Layer | Module | Role |
|-------|--------|------|
| Navigation | `navigation/` | the ten primary areas; preserves context across areas |
| Workflow | `workspaces/` | one workspace per area, building `Page` view-models |
| Visualization | `visualizations/` | deterministic chart specs (bar/line/graph/timeline/table) |
| State | `state/` | loads the snapshot; tracks deterministic `current_*` context |
| Validation | `validation/` | seven presentation-consistency checks |
| Audit | `workspaces/audit.py` | unified browser over every immutable audit log |
| Reporting | `workspaces/reports.py`, `reports/` | report center + static HTML renderer |

`application/` is the composition root (`build_workstation_view`); `schemas/`
holds the view-model contracts (incl. the workstation's *own* `ValidationReport`).

## Primary navigation areas
`System Status` · `Cases` · `Reviews` · `Findings` · `Knowledge` ·
`Intelligence` · `Decision Support` · `Audit` · `Lineage` · `Reports`.

## Workstation validation (consistency, not recomputation)
`validate_state` confirms the view is coherent and fully traceable without
recomputing domain truth: **artifact / registry / version / audit / lineage /
workflow / state** consistency. (It reads the validation/audit/lineage results the
backend already recorded.)

## Decision-support framing
The Decision Support workspace surfaces context, evidence (all of it; nothing
hidden), risk, prioritization, and guidance, and shows the explicit
"clinician remains the decision-maker" statement carried on every record. It
never presents a diagnosis, treatment, medication, or clinical order.

## Quick start
```bash
python -m scripts.build_workstation_snapshot --out workstation_snapshot.json --cases 5
```
```python
from frontend.clinical_workstation import build_from_path, render_workstation_html
view = build_from_path("workstation_snapshot.json")   # WorkstationView
html = render_workstation_html(view)                  # deterministic static HTML
assert view.validation["ok"]
```

Run the tests: `pytest tests/test_clinical_workstation.py`.
See [`docs/V2_P7_CLINICAL_WORKSTATION.md`](./docs/V2_P7_CLINICAL_WORKSTATION.md).
