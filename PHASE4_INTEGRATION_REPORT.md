# Phase 4 — Clinical Report Page: Backend Integration & Placeholder Elimination
## Integration Report & Validation Evidence

## 1. Root-Cause Analysis

Every broken / placeholder-ridden component on the Clinical Intelligence Report
page traced back to a small set of backend/frontend defects. No UI redesign or
model retraining was required.

| # | Root Cause | Files | Impact |
|---|------------|-------|--------|
| RC-1 | **Constants defined AFTER first use.** `EEG_CHANNELS` and `LEAD_TO_ZONE_MAP` were defined at module bottom (≈line 801) but referenced inside `POST /api/v1/calibrate` (line 240+). Every calibrate request raised `NameError`, hit the `except` branch, and returned `{"status":"ERROR"}`. The session was therefore never marked `is_calibrated=True`, so `GET /api/v1/analysis/{id}` returned the empty skeleton and the report page permanently showed "AWAITING INGESTION / 0%" placeholders. | `serve_local.py` | CRITICAL — entire report was dead |
| RC-2 | **Session dict clobbered on predict.** `sess.update({...last_prediction})` in `/predict` overwrote the active session, discarding the `telemetry` dict that `/calibrate` wrote. The telemetry-fallback report builder received `{}` and fell back to defaults. | `serve_local.py` | High — fallback path useless |
| RC-3 | **Channel-name matcher only handled referential labels.** The fuzzy matcher did `raw_ch.upper().replace("-","")`, which worked for `Fp1` but not for bipolar montages (e.g. CHB-MIT `FP1-F7`, `T8-P8-0`). Bipolar recordings — the majority of real EDF corpora — produced `channels=0` and all zeros. | `serve_local.py` | High — real CHB-MIT files showed "0 channels" |
| RC-4 | **Subject-id extraction looked only at `subject_info['id']`.** MNE exposes CHB-MIT subjects under `his_id`. Patient id collapsed to the hash fallback; and it was a **non-deterministic** `hash()` (PYTHONHASHSEED randomised per-process), so calibrate and predict generated different analysis_ids breaking the id chain. | `serve_local.py` | Medium — cross-page id mismatch |
| RC-5 | **Timestamp was a SHA-derived fake date** (`2026.06.DD HH:MM UTC`) instead of the EDF header `meas_date`. Report always showed a fabricated date. | `serve_local.py` | Medium — fabricated metadata |
| RC-6 | **`info['meas_id']` is a tuple in MNE**, not a string. `str(tuple)` was written into `recording_identifier`, producing `"('...',)"` garbage. | `serve_local.py` | Low — cosmetic |
| RC-7 | **Narrative text was hardcoded / fabricated.** It claimed "Spike-Wave Discharges observed", "all 19 channels", "alpha-beta distributions maintained" regardless of signal. The "19 channels" literal was wrong for any recording that wasn't a 19-channel referential montage. | `serve_local.py` | High — simulated medical language |
| RC-8 | **Prediction response omitted real EDF metadata** (channel count, duration, sampling rate, recording start time, filename). The report page had no way to show values consistent with the upload wizard. | `serve_local.py` | Medium — upload↔report consistency broken |
| RC-9 | **`/patients` route served `analysis.html`** instead of `patients.html`. | `serve_local.py` | Low — nav bug |
| RC-10 | **Latency in telemetry-fallback report was hardcoded to `0.0`.** | `serve_local.py` | Low |
| RC-11 | **`GET /api/v1/analysis/{id}` overwrote `risk.model_confidence`** with `p*100+8`, which replaced the model-computed confidence with a probability-derived proxy, re-introducing the very bug that Phase 3.1 had fixed. | `serve_local.py` | Medium — confidence readout wrong |
| RC-12 | **`raw_channel_count` was read after `pick_channels()`**, yielding the post-pick count instead of the original EDF channel count. | `serve_local.py` | Low |
| RC-13 | **Case Intelligence panel had no explicit "empty" state** — a 1-line "No matching cohort profiles available…" was shown. The panel now renders an explicit "No comparable historical cases available" card when `similar_cases=[]`. | `analysis.html` | Low |
| RC-14 | **Report page had no EDF metadata strip** showing filename/channels/sampling-rate/duration, so upload-page ↔ report-page consistency was invisible to the clinician. | `analysis.html` | Medium — cross-page consistency |

---

## 2. Files Modified

| File | Why |
|------|-----|
| `serve_local.py` | Moved constants above their first use (RC-1); robust bipolar-aware channel matcher (RC-3); deterministic patient id via sha256 with MNE `his_id`/`id`/`name` fallback (RC-4); real `meas_date` timestamp (RC-5); fixed `meas_id` tuple handling (RC-6); rewrote narrative & findings to be data-driven with no fabricated clinical language (RC-7); preserved `telemetry` across predict (RC-2); real wall-clock latency (RC-10); `raw_channel_count` captured before `pick_channels()` (RC-12); added `metadata` block (channels, sr, duration, recording_start_time) to prediction & telemetry-fallback responses (RC-8); stopped overwriting model_confidence in report merge (RC-11); fixed `/patients` route (RC-9). |
| `analysis.html` | Added recording-metadata strip (filename/channels/samplerate/duration) bound to backend `metadata.*` (RC-14); added `fmtDuration` helper; `renderCases` now shows an explicit "No comparable historical cases available" empty state (RC-13); `renderRecordingMeta` keeps header patient-id/date bound to `payload.patient_id` / `payload.timestamp`. |

No other files were modified. No CSS, no layout, no new pages, no new APIs, no model changes.

---

## 3. Exact Line Numbers & Before/After Snippets

### 3.1 RC-1 — Constants defined before `/calibrate` (serve_local.py)

**Before (original, after line ~480):**
```python
@app.post("/api/v1/calibrate", response_class=JSONResponse)
async def calibrate_signal(file: UploadFile = File(...)):
    ...
    for ch in EEG_CHANNELS:                    # NameError here
        ...
```
(later, at line ~801, after both routes):
```python
EEG_CHANNELS = ["Fp1","Fp2",...,"Pz"]
LEAD_TO_ZONE_MAP = {...}
```

**After (constants defined at line ~204, BEFORE `/api/v1/calibrate`):**
```python
EEG_CHANNELS = [
    "Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2",
    "F7", "F8", "T3", "T4", "T5", "T6", "Fz", "Cz", "Pz"
]
LEAD_TO_ZONE_MAP = { "Fp1":"FRONTAL", ... }

_CH_ALIASES = {"T7":"T3","T8":"T4","P7":"T5","P8":"T6"}

def _norm_channel_name(raw): ...
def _match_edf_channels(raw_ch_names, expected=EEG_CHANNELS): ...
def _extract_patient_id(info, fallback_stem="eeg"): ...
def _stable_analysis_id(stem): ...

@app.post("/api/v1/calibrate", ...)
async def calibrate_signal(...):
    ...
```
The duplicate definitions at the bottom were removed.

### 3.2 RC-3 — Bipolar-aware channel matcher (serve_local.py)

**Before:**
```python
for ch in EEG_CHANNELS:
    for raw_ch in info['ch_names']:
        clean_raw = raw_ch.upper().replace("EEG","").replace("-","").replace("REF","").replace(" ","")
        if clean_raw == ch.upper():
            channel_mapping[ch] = raw_ch; found_channels_in_raw.append(raw_ch); break
```
(Yielded 0 matches for `FP1-F7`, `F7-T7`, `T8-P8-0`.)

**After:**
```python
def _match_edf_channels(raw_ch_names, expected=EEG_CHANNELS):
    # Robust matcher that handles referential (Fp1), bipolar (FP1-F7), and
    # extended 10-10 labels (T7/T8/P7/P8 → T3/T4/T5/T6 aliases), plus MNE's
    # duplicate-renumber suffix (T8-P8-0).
    ...
channel_mapping, found_channels_in_raw = _match_edf_channels(info['ch_names'])
```
For chb01_01.edf this now yields all 19 canonical leads mapped.

### 3.3 RC-4/RC-5 — Deterministic ID + real EDF timestamp (serve_local.py)

**Before:**
```python
patient_id = subject_info.get('id', 'UNKNOWN')
...
"analysis_id": f"NV-{abs(hash(file.filename or 'eeg')) % 9000 + 1000}-X",
...
_pid_hash = hashlib.sha256(patient_id.encode("utf-8")).hexdigest()
_day = 1 + (int(_pid_hash[:2], 16) % 27)
...
session_timestamp = f"2026.06.{_day:02d} {_hour:02d}:{_minute:02d} UTC"
```

**After:**
```python
patient_id = _extract_patient_id(info, fallback_stem=file.filename or "eeg")
...
"analysis_id": _stable_analysis_id(file.filename or "eeg"),
...
if _recording_start:
    session_timestamp = _recording_start.replace("T"," ").replace("Z"," UTC")
else:
    session_timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
```

### 3.4 RC-7 — Narrative rebuilt from real values (serve_local.py, `/predict`)

**Before:**
```python
supporting_factors = [
    {"name": "Spike-Wave Discharges",
     "description": f"Frequent epileptiform discharges observed in {dominant_lead}."},
    {"name": "Spectral Shift",
     "description": "Delta-theta dominance in the localized region."},
]
...
"across all 19 channels."
```
(Fabricated clinical claims + hardcoded channel count.)

**After:**
```python
narrative_text = (
    f"The submitted EDF recording ({file.filename}, {_mapped_count} mapped "
    f"channels, {_sfreq:.0f} Hz, {_duration_s:.0f} s) shows highest signal "
    f"variance localised to lead {dominant_lead} in the {dominant_zone} region. "
    f"Spectral analysis indicates {spectral_focus.lower()} activity. The model "
    f"computed a peak seizure probability of {risk_probability_pct}% "
    f"({'high' if calculated_probability > 0.85 else 'moderate'} concern tier). "
    f"Signal quality is rated {quality_label.lower()} ({quality_score}/100)."
)
supporting_factors = [
    {"name": "Focal Variance Concentration",
     "description": f"Highest channel variance observed at lead {dominant_lead}."},
    {"name": "Spectral Profile",
     "description": f"{spectral_focus} pattern across mapped channels."},
]
```

### 3.5 RC-8 — Real metadata in response (serve_local.py)

**Before:** `"metadata": {"total_windows_in_buffer": ...}` (only windows).

**After:**
```python
"metadata": {
    "total_windows_in_buffer": _total_windows,
    "channels": _mapped_count,
    "raw_channel_count": _n_raw_channels,
    "sampling_rate_hz": _sfreq,
    "duration_seconds": round(_duration_s, 2),
    "recording_start_time": _recording_start,
}
```

### 3.6 RC-2 — Session update preserves telemetry (serve_local.py)

**Before:**
```python
sess = _ACTIVE_SESSION.get("active_session") or {}
sess.update({"analysis_id":..., "filename":..., "is_calibrated":True, "last_prediction": response_payload})
_ACTIVE_SESSION["active_session"] = sess
```

**After:**
```python
sess = _ACTIVE_SESSION.get("active_session") or {}
prev_telemetry = sess.get("telemetry")
sess.update({"analysis_id":patient_id, "filename":file.filename,
             "is_calibrated":True, "last_prediction": response_payload})
if prev_telemetry is not None:
    sess["telemetry"] = prev_telemetry
_ACTIVE_SESSION["active_session"] = sess
```

### 3.7 RC-11 — Do not overwrite model_confidence (serve_local.py)

**Before:**
```python
alerts = report.get("clinical_alerts_detected") or []
if alerts and alerts[0].get("peak_seizure_probability") is not None:
    report["risk"]["model_confidence"] = round(max(40.0, min(99.0,
        float(alerts[0]["peak_seizure_probability"]) * 100.0 + 8.0)), 1)
```

**After:**
```python
_live_risk = latest.get("risk") or {}
if _live_risk.get("model_confidence") is not None:
    report.setdefault("risk", {})["model_confidence"] = _live_risk["model_confidence"]
```

### 3.8 RC-14 — Metadata strip added to report page (analysis.html)

**Before:** (no strip — channels/duration/sr were invisible on report page)

**After:** a four-field strip inserted under the "Clinical Risk Assessment" heading:
```html
<div id="recording-meta-row" class="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-[11px] font-label-sm text-label-sm font-mono">
  <span class="text-outline">FILE:</span><span id="meta-filename" class="text-on-surface">—</span>
  <span class="w-px h-3 bg-outline-variant/50"></span>
  <span class="text-outline">CHANNELS:</span><span id="meta-channels" class="text-on-surface">—</span>
  <span class="w-px h-3 bg-outline-variant/50"></span>
  <span class="text-outline">SAMPLING:</span><span id="meta-samplerate" class="text-on-surface">—</span>
  <span class="w-px h-3 bg-outline-variant/50"></span>
  <span class="text-outline">DURATION:</span><span id="meta-duration" class="text-on-surface">—</span>
</div>
```
populated by `renderRecordingMeta(payload)` which binds to `payload.metadata.channels / sampling_rate_hz / duration_seconds / filename`.

### 3.9 RC-13 — Honest empty state for Case Intelligence (analysis.html)

**Before:** `<li>` text "No matching cohort profiles available until ingestion session starts"

**After:** a card with icon + title "No comparable historical cases available" + explanation that the case repository is not connected in this deployment.

---

## 4. UI → Backend Mapping Table

| UI Component (id) | Backend Field | Status | Fixed |
|-------------------|---------------|--------|-------|
| Header Patient ID (`hdr-pid`) | `patient_id` / `analysis_id` | ✅ correct | — |
| Header Date (`hdr-date`) | `timestamp` | ✅ real (was fabricated hash-date) | RC-5 |
| Recording strip — filename (`meta-filename`) | `filename` | ✅ added | RC-8/14 |
| Recording strip — channels (`meta-channels`) | `metadata.channels` (= calibrate `channels`) | ✅ added | RC-1/3/8/14 |
| Recording strip — sampling (`meta-samplerate`) | `metadata.sampling_rate_hz` | ✅ added | RC-8/14 |
| Recording strip — duration (`meta-duration`) | `metadata.duration_seconds` | ✅ added | RC-8/14 |
| Probability ring/text (`probability-ring`, `probability-text`) | `peak_seizure_probability` → `risk.probability` | ✅ correct (was dead due to RC-1) | RC-1 |
| Risk tier badge (`risk-badge`) | `risk.tier` / `clinical_alerts_detected[0].status` | ✅ correct (now live) | RC-1 |
| Model Confidence (`model-confidence`) | `risk.model_confidence` | ✅ was being overwritten by proxy | RC-11 |
| Prediction Stability (`prediction-stability`) | `risk.prediction_stability` | ✅ correct (now live) | RC-1 |
| Analysis Latency (`analysis-latency`) | `risk.analysis_latency_seconds` (real `time.time()` wall-clock) | ✅ now real | RC-10 |
| Key Finding (`key-finding-text`) | `risk.key_finding` | ✅ rebuilt from real values | RC-7 |
| Secondary Findings list (`secondary-findings-list`) | `risk.secondary_findings[]` | ✅ rebuilt (no fabricated medical claims) | RC-7 |
| Clinical Narrative text (`narrative-text`) | `clinical_narrative.text` | ✅ rebuilt from filename/channels/sr/duration/zone/lead/prob/quality | RC-7 |
| Narrative highlights (`<mark>` spans) | `clinical_narrative.highlights[]` | ✅ data-driven | RC-7 |
| Evidence impact bar (`bar-supporting`, `lbl-supporting`) | `evidence_intelligence.supporting_impact` | ✅ correct (now live) | RC-1 |
| Evidence impact bar (`bar-opposing`, `lbl-opposing`) | `evidence_intelligence.opposing_impact` | ✅ correct (now live) | RC-1 |
| Supporting Factors list | `evidence_intelligence.supporting_factors[]` (name/description) | ✅ rebuilt (no "Spike-Wave" fabrication) | RC-7 |
| Opposing Factors list | `evidence_intelligence.opposing_factors[]` | ✅ rebuilt | RC-7 |
| Spectral label (`spectral-label`) | `brain_intelligence.spectral_dominance.label` | ✅ real Welch PSD (was "Unknown" due to RC-1) | RC-1 |
| Delta bar/value (`delta-bar`, `delta-value`) | `brain_intelligence.spectral_dominance.bands[DELTA].value` | ✅ real PSD pct | RC-1 |
| Theta bar/value | bands[THETA] | ✅ | RC-1 |
| Alpha bar/value | bands[ALPHA] | ✅ | RC-1 |
| Beta bar/value | bands[BETA] | ✅ | RC-1 |
| Head-map layer / loc badge | `brain_intelligence.localization.dominant_zone` | ✅ correct (now live) | RC-1 |
| Localization card — region (`loc-region`) | `localization.region` | ✅ | RC-1 |
| Localization confidence (`loc-confidence`) | `localization.confidence` | ✅ | RC-1 |
| Evidence strength (`loc-strength`) | `localization.evidence_strength` | ✅ | RC-1 |
| Quality ring/value (`quality-ring`, `quality-val`) | `signal_intelligence.quality_score` | ✅ real MNE-derived | RC-1 |
| Quality label (`quality-label`) | `signal_intelligence.quality_label` | ✅ | RC-1 |
| Noise Burden (`noise-val`) | `signal_intelligence.noise_burden` | ✅ µV from MNE std | RC-1 |
| Artifact Burden (`artifact-val`) | `signal_intelligence.artifact_burden` | ✅ derived from quality score | RC-1 |
| Trust bar/value (`trust-bar`, `trust-val`) | `signal_intelligence.trust_level` | ✅ | RC-1 |
| Case cards grid (`cases-grid`) | `case_intelligence.similar_cases[]` | ✅ honest empty-state (never fabricated) | RC-13 |

---

## 5. Verification Evidence (multiple EDF files)

The automated verifier (`verify_phase4.py`) ran calibrate → predict → analysis for
every available EDF and asserted cross-endpoint consistency.

| EDF file | analysis_id | channels | duration | sr (Hz) | prob | tier | zone/lead | spectral | quality |
|----------|-------------|----------|----------|---------|------|------|-----------|----------|---------|
| `chb_test/chb01/chb01_01.edf` (real CHB-MIT, 1h) | NV-8176-X | **19** / 19 ✓ | 3600.0 s | 256 | 69.0% | MODERATE | FRONTAL / Fp1 | Delta-Dominant (73/14/3/10) | 100 Optimal |
| `tests/fixtures/eeg/valid.edf` (3-ch synthetic) | NV-4411-X | **3** / 3 ✓ | 2.0 s | 256 | 2.0% | LOW | FRONTAL / Fp1 | Delta-Dominant (100/0/0/0) | 20 Insufficient |
| `tests/fixtures/eeg/valid_edf_plus.edf` | NV-1517-X | **3** / 3 ✓ | 2.0 s | 256 | 2.0% | LOW | FRONTAL / Fp1 | Delta-Dominant | 20 Insufficient |
| `workspace/.../valid_1.edf` | NV-3240-X | **3** / 3 ✓ | 2.0 s | 256 | 2.0% | LOW | FRONTAL / Fp1 | Delta-Dominant | 20 Insufficient |
| `workspace/.../valid_2.edf` | NV-5818-X | **3** / 3 ✓ | 2.0 s | 256 | 2.0% | LOW | FRONTAL / Fp1 | Delta-Dominant | 20 Insufficient |

Cross-page consistency assertion passed for every file:
```
[OK] Upload-page ↔ Report-page consistency: CHANNELS / SR / DURATION all match
```
Cross-file variation assertion passed: probabilities and quality scores differ
between the real CHB-MIT recording and the synthetic fixtures (69% vs 2%, quality
100 vs 20) proving the report is driven by signal content, not hardcoded values.

The four `valid*.edf` fixtures are byte-identical 2-second 3-channel near-flat
sine waves, so their outputs are correctly identical to each other.

Raw JSON responses and a captured HTML snapshot of the analysis page are saved
to `verification_evidence/`:
- `01_calibrate_chb01_01.json`
- `02_predict_chb01_01.json`
- `03_analysis_chb01_01.json`
- `04_analysis_page.html`

---

## 6. Final Validation Checklist

- [x] No simulated/archetype/seeded-random/fake values on the report page
- [x] Every visible value originates from the backend (`/api/v1/analysis/{id}`)
- [x] Report changes when different EDF files are analysed (69% on CHB-MIT vs 2% on synthetic)
- [x] Upload page and Report page show consistent channels / sampling rate / duration / probability / confidence / localization / patient id
- [x] No fabricated medical language ("Spike-Wave Discharges", "epileptiform discharges" — removed; replaced with honest signal-derived descriptions)
- [x] Case Intelligence shows honest "No comparable historical cases available" state (never invents cases)
- [x] Timestamp is the real EDF `meas_date`, not a fabricated hash-date
- [x] Patient id is deterministic across processes (sha256, not `hash()`)
- [x] Bipolar-montage EDFs (CHB-MIT) correctly map all 19 canonical 10-20 leads
- [x] `is_calibrated:false` path (unknown id) still returns an honest empty skeleton, not fake data
- [x] No UI redesign, no CSS rewrites, no new pages, no new APIs, no model changes
- [x] Only two files modified: `serve_local.py` and `analysis.html`
