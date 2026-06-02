# `frontend/offline_research_app/` — Offline Research Application (V1-P8)

> **Layer:** Presentation (`frontend/`) · **Status:** Implemented (offline, V1-P8).
> **Decision record:** [`../../.gcc/decisions/ADR-0002`](../../.gcc/decisions/ADR-0002-v1-p7-p8-offline-inference-and-research-app.md)
> **Governing docs:** AP-4/NR-4 (faithful uncertainty), AP-7/NR-8 (boundaries)

A presentation-only research workstation. It loads the offline inference
platform's **registered artifacts** (JSON) and renders them as view-models and a
single, dependency-free, **offline** HTML report. It computes nothing.

---

## The strictest boundary (NR-8)

The frontend imports **no domain module** — not `ml`, `evaluation`, `datasets`,
`preprocessing`, nor even `backend` as code. Standard library only. In the offline
setting the frontend↔backend boundary is a **data/file boundary**: the backend
writes registered artifacts; the frontend reads them. The UI literally *cannot*
recompute a domain value because it cannot import domain code. Enforced by
`tests/test_boundaries.py` (`frontend` imports nothing internal).

## Workflows (all from registered artifacts)

| # | Workflow | Shows |
|---|----------|-------|
| 1 | **Upload** | file validation · metadata · quality report · readiness report |
| 2 | **Dataset Intelligence** | dataset/patient/channel profiles · quality · leakage · readiness |
| 3 | **Inference** | prediction · probability · calibration · conformal set · coverage · risk · status · version bundle |
| 4 | **Benchmark** | model benchmarks · evaluation · split info · metric reports · history |
| 5 | **Audit** | lineage · artifacts · registries · version history · decision & validation trail |

## Visualizations (11)

EEG metadata · channel layout · dataset statistics · class distribution ·
evaluation metrics · calibration curve · coverage curve · risk profile · benchmark
comparison · lineage graph · version graph — emitted as deterministic chart specs,
rendered as inline SVG in the static HTML (no JS, no external assets).

## Subsystems

`state/` (load registered artifacts) · `schemas/` (view-model contracts +
the app's own `ValidationReport`) · `components/` (kv/table/badges/text) ·
`visualizations/` (chart specs) · `workflows/` (the 5 workflows) · `pages/`
(assemble the `AppView`) · `validation/` (`AppValidator` — artifact/registry/
output/version/lineage consistency) · `reports/` (static offline HTML renderer).

## Run it

```bash
python -m scripts.run_offline_inference --render-app    # writes research_app.html
```

```python
from frontend.offline_research_app import AppState, build_app_view, render_from_run_dir
view = build_app_view(AppState.load(run_dir))   # presentation-only view-model
html = render_from_run_dir(run_dir)             # deterministic, offline HTML
```

Faithful uncertainty (NR-4): every per-window record shows its calibrated
confidence and conformal set; nothing is flattened to a bare label.

See [`docs/V1_P8_RESEARCH_APP.md`](./docs/V1_P8_RESEARCH_APP.md).
