# NeuroVision AI Latest Repo Patch

Built against the latest `aghilan28/neurovision_ai` repo that includes:

- `analysis.html`
- `serve_local.py`
- active `/analysis/{id}` routing
- session integration

## Copy directly into project root

This folder is intentionally project-root aligned. If your local repo root is the folder where `code.html`, `analysis.html`, and `serve_local.py` already exist, copy all contents of this folder directly into that root.

Expected final paths:

```text
repo-root/code.html
repo-root/analysis.html
repo-root/serve_local.py
repo-root/neurovision_api.py
repo-root/assets/brain_localization/Frontal.png
repo-root/assets/brain_localization/L-Temporal.png
repo-root/assets/brain_localization/R-Temporal.png
repo-root/assets/brain_localization/central.png
repo-root/assets/brain_localization/Parietal.png
```

## What changed

### analysis.html

- Replaced the embedded/static brain picture section with a live layer-switching localization viewport.
- Uses finalized images from `https://github.com/aghilan28/neuro_brain` only.
- Consumes `brain_intelligence.localization.dominant_zone` when available.
- Also supports the current analysis report fields by deriving zone from `dominant_lead`/`region`.
- Cross-fades use exactly:

```css
transition: opacity 400ms cubic-bezier(0.4, 0, 0.2, 1)
```

### code.html

- Keeps the live `/api/v1/predict` JSON integration targeting:

```js
response.brain_intelligence.localization.dominant_zone
```

- The “View Intelligence Report” button now routes to `/analysis/{active_session_id}`.

### serve_local.py

- Preserves your `/analysis/{id}` serving route.
- Updates JSON `/api/v1/predict` to return the production localization contract.
- Keeps legacy multipart NDJSON behavior for older pipeline flows.
- Enriches `/api/v1/analysis/{id}` with latest live localization from session state when available.

### neurovision_api.py

- Allows `/api/v1/predict` backend parsing to accept either `data` or `features` arrays.

## Images

These files were copied from your `neuro_brain` repo:

- `Frontal.png`
- `L-Temporal.png`
- `R-Temporal.png`
- `central.png`
- `Parietal.png`

No generated/made-up regional images are included.
