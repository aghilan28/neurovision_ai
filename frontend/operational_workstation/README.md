# `frontend/operational_workstation/` — Operational Intelligence Workstation (V3-P7)

> **Layer:** Presentation (`frontend/`) — imports **no** domain module (NR-8)
> **Status:** Implemented (V3-P7)
> **Governing docs:** AP-5/AP-8 (traceability/audit), AP-6 (reproducibility),
> AP-7/NR-8 (boundaries), AP-9 (versioned decisions);
> [`../../docs/architecture/IMPORT_RULES.md`](../../docs/architecture/IMPORT_RULES.md), ADR-0010

The first **unified operational environment** — the primary interface over every
Version 3 subsystem. An operator navigates **Events → Timelines → Workflows → Graph
→ Analytics → Recommendations**, plus unified **Audit**, **Lineage**, **Reports**,
and a **System Health** landing area, through one coherent environment.

---

## It exposes the operational system; it is not a source of truth
Everything displayed originates from **registered artifacts**: registries,
registered reports, immutable audit logs, the shared lineage graph, and recorded
validation results. The workstation **creates no operational logic** — it is not a
workflow engine, an analytics engine, or a recommendation engine. The only state it
tracks is *deterministic navigation context* (current event/timeline/workflow/…).

## The boundary (NR-8) and how it is honored
`frontend/` may import **nothing internal** (the strictest rule, enforced by
`tests/test_boundaries.py::test_frontend_imports_no_domain_module`). So the
workstation never imports `backend`/`ml`/etc. Instead:

1. **`scripts/build_operational_workstation_snapshot.py`** (which *may* import
   backend) composes the real V3 services over **one shared lineage tracker**, runs
   a small deterministic multi-case workflow, and serializes every registered
   artifact into a single JSON **snapshot**.
2. **The workstation** reads that snapshot with stdlib `json` only and renders it.

```
backend V3 services ─(scripts.build_operational_workstation_snapshot)→ snapshot.json → frontend.operational_workstation
   (source of truth)                                                    (registered        (presentation only,
                                                                          artifacts)         stdlib json only)
```

## Architecture (the six workstation layers)
| Layer | Module | Role |
|-------|--------|------|
| Navigation | `navigation/` | the ten primary areas; preserves context across areas |
| Workspace | `workspaces/` | one workspace per area, building `Page` view-models |
| Visualization | `visualizations/` | the ten deterministic chart families |
| State | `state/` | loads the snapshot; tracks deterministic `current_*` context |
| Validation | `validation/` | six presentation-consistency checks |
| Reporting | `reports/` | the report center renderer + static offline HTML |

`application/` is the composition root (`build_workstation_view`); `schemas/`
holds the view-model contracts (incl. the workstation's *own* `ValidationReport`).

## Primary navigation areas (ten)
`System Health` · `Events` · `Timelines` · `Workflows` · `Graph` · `Analytics` ·
`Recommendations` · `Audit` · `Lineage` · `Reports`.

## The ten visualization families
Event streams · timeline evolution · workflow flows · dependency networks · graph
structures · analytics trends · risk trends · recommendation priorities · audit
timelines · lineage graphs (all deterministic chart specs; rendered as inline SVG).

## Workstation validation (consistency, not recomputation)
`validate_state` confirms the view is coherent and fully traceable without
recomputing domain truth: **registry / audit / lineage / visualization / report /
state** consistency. (It reads the validation/audit/lineage results the backend
already recorded.)

## Recommendation framing
The Recommendations workspace surfaces guidance, priorities, optimization
suggestions, and escalation **candidates**, each with its evidence and analytics
links, and states explicitly that these are **operational suggestions only** — not
clinical decision support, diagnosis, or treatment, and never executed or
auto-escalated.

## Quick start
```bash
python -m scripts.build_operational_workstation_snapshot --out op_snapshot.json --cases 3
```
```python
from frontend.operational_workstation import build_from_path, render_workstation_html
view = build_from_path("op_snapshot.json")            # WorkstationView
html = render_workstation_html(view)                  # deterministic static HTML
assert view.validation["ok"]
```

Run the tests: `pytest tests/test_operational_workstation.py`.
See [`docs/V3_P7_OPERATIONAL_WORKSTATION.md`](./docs/V3_P7_OPERATIONAL_WORKSTATION.md).
