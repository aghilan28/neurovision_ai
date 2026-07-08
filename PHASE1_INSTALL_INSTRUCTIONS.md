# Phase 1 Installation Instructions

## How to apply these files to your repo

These 3 files go in your **project root** (the `neurovision_ai/` directory):

```
neurovision_ai/
├── serve_local.py                  ← REPLACE (was 58KB, now 74KB)
├── Dockerfile                      ← REPLACE (was 570B, now 524B)
├── PHASE1_BACKEND_RECOVERY_REPORT.md  ← NEW (add to repo)
├── code.html                       ← NOT TOUCHED
├── upload.html                     ← NOT TOUCHED
├── dashboard.html                  ← NOT TOUCHED
├── auth.html                       ← NOT TOUCHED
├── analysis.html                   ← NOT TOUCHED
├── status.html                     ← NOT TOUCHED
├── patients.html                   ← NOT TOUCHED
├── neurovision_api.py              ← NOT TOUCHED (kept as reference)
├── PHASE5B_TEMPORAL_XGBOOST.joblib ← NOT TOUCHED
└── ... (everything else unchanged)
```

## Steps

1. Extract the zip
2. Copy the 3 files into your `neurovision_ai/` project root, replacing the originals
3. Commit and push

```bash
# From your local repo clone:
cp /path/to/extracted/neurovision_ai/serve_local.py .
cp /path/to/extracted/neurovision_ai/Dockerfile .
cp /path/to/extracted/neurovision_ai/PHASE1_BACKEND_RECOVERY_REPORT.md .

git add serve_local.py Dockerfile PHASE1_BACKEND_RECOVERY_REPORT.md
git commit -m "Phase 1: Backend Foundation Recovery - unified server architecture"
git push
```

## To run locally

```bash
pip install fastapi uvicorn python-multipart mne numpy joblib xgboost scikit-learn
python serve_local.py
# → http://localhost:8080
```

## To run with Docker

```bash
docker build -t neurovision .
docker run -p 8080:8080 neurovision
```
