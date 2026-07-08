# NeuroVision AI — Phase 1: Backend Foundation Recovery Report

**Date:** 2026-07-08  
**Status:** ✅ COMPLETE  
**Scope:** Backend architecture consolidation — zero frontend/model/UI changes

---

## 1. Repository Audit Findings

### 1.1 Server Entry Points Identified (BEFORE Phase 1)

| # | File | Port | Purpose | Problem |
|---|------|------|---------|---------|
| 1 | `serve_local.py` | 8080 | Frontend-facing backend — serves HTML, handles EDF uploads via MNE | ⚠️ Had wrapper import fallbacks, fake calibration responses |
| 2 | `neurovision_api.py` | 8080 | Standalone model API — accepts JSON feature matrices, runs XGBoost+BiLSTM | ❌ Incompatible with code.html (expects features, not files); no HTML serving |
| 3 | `backend/application_platform/server/app.py` | 8000 | Enterprise backend — full auth, model provisioning, persistence | ❌ Complex dependency chain, crashes without specialized artifacts |
| 4 | `scripts/serve_neurovision.py` | 10000 | Render deployment wrapper | ❌ Delegates to #3 |
| 5 | `scripts/application_frontend_gateway.py` | N/A | Cookie-based HTML route layer | ❌ Attaches to #3 |

### 1.2 Duplicate Execution Paths Found

- **`/api/v1/calibrate`** — defined in BOTH `serve_local.py` (file upload) AND `neurovision_api.py` (JSON)
- **`/api/v1/predict`** — defined in BOTH `serve_local.py` (file upload) AND `neurovision_api.py` (JSON)
- **`/health`** — defined in 3 different files
- **Root `/`** — defined in 3 different files

### 1.3 Placeholder/Fake Responses Found

| Location | Issue |
|----------|-------|
| `serve_local.py` original | Hardcoded fallback `channels: 19, total_windows_processed: 1112` when wrapper import failed |
| `serve_local.py` original | `try: import neurovision_api` fell back to "simulation mode" |
| `Dockerfile` | Pointed to `neurovision_api.py` which doesn't serve any HTML pages |

### 1.4 Frontend API Dependencies (ALL 7 HTML pages audited)

| Page | File | API Calls Made |
|------|------|----------------|
| Landing/Upload | `code.html` | `POST /api/v1/calibrate` (FormData file), `POST /api/v1/predict` (FormData file), `GET /api/v1/session/current` |
| Upload Wizard | `upload.html` | `POST /v1/uploads` (JSON+base64), `POST /api/v1/calibrate` (JSON features), `POST /api/v1/predict` (JSON features) |
| Analysis Report | `analysis.html` | `GET /api/v1/session/current`, `GET /api/v1/analysis/{id}`, `POST /api/v1/session/current` |
| Dashboard | `dashboard.html` | `GET /health`, `GET /telemetry`, `GET /v1/analyses` |
| Auth Portal | `auth.html` | `GET /health`, `POST /v1/auth/register`, `POST /v1/auth/login`, `POST /api/v1/auth/login`, `POST /api/v1/users/register` |
| Status | `status.html` | `GET /health`, `GET /v1/persistence` |
| Patients | `patients.html` | Static content (no API calls) |

**Critical finding:** `code.html` sends EDF files as FormData, `upload.html` sends JSON feature matrices — the unified backend must handle BOTH content types on the same endpoints.

---

## 2. Phase 1 Implementation

### 2.1 Files Modified

| File | Action | Details |
|------|--------|---------|
| `serve_local.py` | **REBUILT** | Single unified backend handling ALL API contracts |
| `Dockerfile` | **UPDATED** | Points to `serve_local.py`, copies full project |

### 2.2 What Was Fixed

1. **Wrapper imports eliminated** — No more `try: import neurovision_api` / `neurovision_inference` fallback chains
2. **Fake responses removed** — No more hardcoded `channels: 19, total_windows_processed: 1112`
3. **Dual-mode endpoints** — `/api/v1/calibrate` and `/api/v1/predict` now handle BOTH:
   - `code.html` → multipart/form-data EDF file upload
   - `upload.html` → application/json with feature matrices
4. **Real XGBoost inference on JSON path** — When `upload.html` sends features, the loaded Phase 5B model runs real `predict_proba()` (not fake values)
5. **Missing endpoints added** — `/health`, `/telemetry`, auth endpoints, `/v1/persistence`, `/v1/analyses`, `/v1/uploads`
6. **numpy serialization bug fixed** — `_safe_json()` prevents `int64`/`float64` crashes
7. **Session continuity fixed** — predict reuses calibrate's `analysis_id`
8. **Docker entry point fixed** — `ENTRYPOINT ["python", "serve_local.py"]` with full project copy

### 2.3 What Was Preserved (ZERO changes)

- ✅ All 7 HTML pages (`code.html`, `upload.html`, `analysis.html`, `dashboard.html`, `auth.html`, `status.html`, `patients.html`)
- ✅ All CSS and JavaScript (embedded in HTML)
- ✅ Model `PHASE5B_TEMPORAL_XGBOOST.joblib` (loaded at startup, used for JSON-path inference)
- ✅ All MNE EDF parsing logic
- ✅ All archetype-based clinical report generation (5 archetypes)
- ✅ All variance-based localization logic
- ✅ Optional `neurovision_localization.py` module (graceful degradation)
- ✅ All spectral band computation
- ✅ All clinical alert generation

---

## 3. Architecture After Phase 1

```
Browser
  ↓
ONE Frontend (7 HTML pages, unchanged)
  ↓
ONE Backend (serve_local.py — FastAPI on port 8080)
  ├── EDF file path: MNE parsing → signal analysis → clinical payload
  └── JSON feature path: XGBoost model → real inference → prediction payload
  ↓
ONE Trained Model (PHASE5B_TEMPORAL_XGBOOST.joblib, 484 features)
```

---

## 4. Complete Route Registry

| Route | Method | Source | Handler |
|-------|--------|-------|---------|
| `/` | GET | code.html → FormData | Serves code.html (landing page) |
| `/upload` | GET | Navigation | Serves code.html |
| `/dashboard` | GET | Navigation | Serves dashboard.html |
| `/auth` | GET | Navigation | Serves auth.html |
| `/status` | GET | Navigation | Serves status.html |
| `/patients` | GET | Navigation | Serves patients.html |
| `/analysis/{id}` | GET | code.html redirect | Serves analysis.html |
| `/health` | GET | auth.html, dashboard.html | Model readiness JSON |
| `/telemetry` | GET | dashboard.html | Engine telemetry JSON |
| `/v1/analyses` | GET | dashboard.html | Analysis history |
| `/v1/persistence` | GET | status.html | Persistence status |
| `/v1/auth/register` | POST | auth.html | User registration |
| `/v1/auth/login` | POST | auth.html | User login |
| `/api/v1/auth/login` | POST | auth.html | User login (alias) |
| `/api/v1/users/register` | POST | auth.html | Registration (alias) |
| `/api/v1/calibrate` | POST | code.html (file), upload.html (JSON) | **Dual-mode** calibration |
| `/api/v1/predict` | POST | code.html (file), upload.html (JSON) | **Dual-mode** prediction |
| `/api/v1/session/current` | GET | code.html, analysis.html | Session state |
| `/api/v1/session/current` | POST | analysis.html | Session mutation |
| `/api/v1/analysis/{id}` | GET | analysis.html | Clinical report JSON |
| `/v1/uploads` | POST | upload.html | EDF upload (base64) |

---

## 5. Verification Results

### Live Server Test
```
GET /health          → 200  xgb_model_ready=true  model_prepared=true
GET /                → 200  56,196 bytes (code.html)
GET /dashboard       → 200  32,157 bytes
GET /auth            → 200  35,859 bytes
POST /api/v1/calibrate (JSON)  → 200 SUCCESS
POST /api/v1/predict (JSON)    → 200 SUCCESS
GET /telemetry       → 200
```

### XGBoost Model Inference Verified
```
Calibrate (JSON): XGBoost baseline mu=0.001377 sigma=0.002024 gate=0.5000
Predict (JSON):   XGBoost peak_prob=0.004084
```

### 41/41 Automated Checks Passed
- 7 page routes ✅
- 5 infrastructure endpoints ✅
- 5 auth endpoints ✅
- 8 code.html EDF flow ✅
- 9 upload.html JSON flow ✅
- 4 /v1/uploads flow ✅
- 1 session continuity ✅
- 2 architecture checks ✅

---

## 6. Phase 1 Checklist

- [x] Application starts correctly on port 8080
- [x] ONE backend architecture exists (`serve_local.py`)
- [x] Duplicate execution paths removed
- [x] Wrapper applications eliminated
- [x] Placeholder/fake responses removed
- [x] All frontend API contracts satisfied (dual-mode calibrate + predict)
- [x] Real XGBoost inference on JSON feature path
- [x] Routing repaired for ALL 7 HTML pages
- [x] Existing frontend preserved (zero HTML/CSS/JS changes)
- [x] Model loaded and operational
- [x] Dockerfile updated
- [x] Ready for Phase 2

---

## 7. Deployment Instructions

```bash
# Local development
cd neurovision_ai
python serve_local.py
# → Server starts on http://0.0.0.0:8080

# Docker
docker build -t neurovision .
docker run -p 8080:8080 neurovision
```

---

## 8. Phase 2 Scope (NOT started)

- Connect XGBoost model to the EDF-file predict path (replace variance-based probability)
- Wire the 484-feature extraction pipeline for raw EDF → feature matrix → model inference
- Connect BiLSTM deep sequential engine for temporal event detection
- Replace archetype-based reports with model-driven reports
