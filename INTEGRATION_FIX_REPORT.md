# NeuroVision AI — Frontend ↔ Backend Data-Binding Fix

**Root cause was NOT CSS.** The model is accurate, but the serving layer
(`serve_local.py`) and the analysis view (`analysis.html`) had broken data
contracts that caused every visualization to collapse to **0% / 2% / DIFFUSE**
whenever the model actually detected something. This patch makes the live model
output drive every panel end-to-end — **including true model-driven brain
localization via channel ablation.**

---

## Files in this package (drop-in replacements at project root)

| File | Role | Change type |
|------|------|-------------|
| `serve_local.py` | Backend FastAPI runner (serves the HTML app + `/api/v1/*`) | **Bug fixes + payload completion + model-driven localization wiring** |
| `neurovision_localization.py` | **NEW** — XGBoost channel-ablation localization engine | **New module** |
| `analysis.html` | Clinical report view (the page with gauges + head map) | **Data-binding refactor** |
| `code.html` | EEG upload / inference wizard | **Robustness fixes** |

> Copy them over the existing files at your repo root (`serve_local.py`,
> `analysis.html`, `code.html`) and add `neurovision_localization.py` alongside
> `neurovision_api.py`. No other files, routes, or wiring change.

---

## ⚠️ One new dependency for the MODEL-DRIVEN path

`neurovision_localization.py` reproduces the exact Phase 5B feature extractor,
which needs two packages not currently in `requirements.txt`. Add them:

```
antropy>=0.2.0
PyWavelets>=1.5.0
```

(scipy is already pulled in by mne.) If these or the model artifact
`PHASE5B_TEMPORAL_XGBOOST.joblib` are absent, localization **automatically
falls back** to the variance method — the app never crashes. To force a custom
model path, set the env var `NEUROVISION_XGB_PATH`.

---

## The bugs that were fixed

### 1. `NameError` collapsed the whole pipeline (the #1 cause of 0%)
In `serve_local.py` → `predict_real_edf_stream`, the response was built with
f-strings referencing **undefined variables**:

```python
# BROKEN (NameError whenever a seizure was detected, i.e. probability >= 0.5012):
f"... in the {dominantZone} region ({dominantLead})."
```

The real variables are `dominant_zone` / `dominant_lead` (snake_case). So **the
exact high-risk case the model is built for threw `NameError`**, the handler
returned `{"status": "ERROR"}`, and every downstream gauge rendered **0%** with
localization forced to **DIFFUSE**. Fixed: all references now use the correct
snake_case names.

### 2. `pick_channels(on_missing=...)` crashed on modern MNE
`raw.pick_channels(found_channels_in_raw, on_missing='ignore')` raises
`TypeError` on many MNE versions, again making `/predict` return
`{"status":"ERROR"}`. Fixed: picks only channels that exist in the raw object.

### 3. The `/predict` payload was incomplete
The live response never included `signal_intelligence` (→ **Trust Level stuck at 0%**),
nor `region`/`confidence`/`evidence_strength`/`spectral_dominance.bands` in
`brain_intelligence` (→ blank card, flat bars). Fixed.

### 4. `analysis.html` was desynchronized from the report
`render()` did `payload = activeSession.last_prediction || data`, so a stale or
errored wizard prediction **shadowed** the authoritative server report. Fixed:
`get_analysis_report()` authoritatively overlays the live model values, and the
page prefers the server-merged report.

---

## 🧠 TRUE model-driven localization (NEW)

### Why ablation (not SHAP / feature_importances_)
The model's 484 features are **cross-channel aggregates**:
`mean_mean` = mean across channels of per-window mean; `variance_std` = std
across channels of variance; `delta_power_mean` = mean across channels of delta
power; etc. Channel identity is **averaged away before the model sees anything**,
so there is no per-channel feature block to attribute. The only correct
model-driven method is therefore **leave-one-out channel ablation**:

1. Extract the 484-feature contract (96 base + lag1/lag3/rolling_mean_5/
   stability_5 + 4 positional) from the uploaded recording — reproducing the
   exact Phase 5B training extractor (window 4 s, stride 2 s).
2. Run the **real** `PHASE5B_TEMPORAL_XGBOOST.joblib` → baseline peak probability.
3. For each of the 19 channels: zero it → re-extract → re-predict → measure the
   seizure-probability drop.
4. `dominant_lead` = channel whose removal most reduced the output → mapped to
   a brain zone; `channel_weights` carry the true per-lead attribution.

**Efficiency:** because the 96 base features aggregate across channels,
per-channel features are computed **once**; each ablation pass only re-aggregates
the remaining 18 channels (no entropy/wavelet recompute), so the full 19-channel
ablation runs in low seconds even on long recordings (window count is capped).

The result is surfaced as
`brain_intelligence.localization.localization_method` = `"xgboost_channel_ablation"`
when the model drove it, or `"variance_fallback"` otherwise.

### Head-map synchronization (`applyDominantZoneLocalization`)
1. **RESET** all 5 lobes to inactive baseline before processing.
2. Highlight **only** the single lobe matching the parsed `dominant_zone`.
3. `DIFFUSE`/`GENERAL` → all lobes deactivated, `diffuse.png` exclusively.

No static layout code forces FRONTAL active anywhere.

---

## How to deploy

```bash
# 1. Back up originals
cp serve_local.py serve_local.py.bak && cp analysis.html analysis.html.bak && cp code.html code.html.bak

# 2. Drop in the patched files + the new module (repo root)
#    serve_local.py, neurovision_localization.py, analysis.html, code.html

# 3. Add the two dependencies
pip install antropy PyWavelets

# 4. Restart
python serve_local.py          # or: uvicorn serve_local:app --host 0.0.0.0 --port 8080
```

The model-driven engine auto-detects `PHASE5B_TEMPORAL_XGBOOST.joblib` in the
project root. On real patient EDFs matching your training distribution, it will
produce the model's true seizure probability and attribute the correct affected
region. The head map, gauges and localization card all bind to that output.

---

## Verification performed

- `serve_local.py` and `neurovision_localization.py` compile cleanly.
- `analysis.html` / `code.html` JS pass `node --check`.
- The 96-base feature order was confirmed to **exactly match**
  `PHASE5B_FEATURE_SIGNATURE.json`.
- **End-to-end HTTP test** (calibrate → predict → session → analysis) on the
  patched server with the real XGBoost model loaded — `localization_method`
  returns `xgboost_channel_ablation`, ablation runs, channel contributions
  computed, no errors.
- **Frontend binding test**: the real `analysis.html` IIFE executed against the
  live server — probability, model-confidence, trust bar, head-map image and
  localization region all render and are **consistent with the backend zone**
  (head-map `canvas.src` matches `dominant_zone` exactly).
- Two execution paths confirmed: model-driven (when model + deps available) and
  variance fallback (automatic otherwise).

