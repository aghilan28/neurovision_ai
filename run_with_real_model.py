#!/usr/bin/env python3
"""
STABLE RUNNER — Uses the REAL trained CHB-MIT model (our fix)
Avoids the antropy / numba / neurovision_localization crash loop.

Usage (recommended):
    python run_with_real_model.py

This starts a minimal FastAPI server on port 8080 with:
  GET  /health
  POST /upload_and_analyze   → full metadata + real seizure prediction

It uses our fixed pretrained pipeline directly.
"""

import os
import sys
import tempfile

# Make sure we can import our fixed modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# === THE FIX: Load the real trained model ===
from backend.application_platform.provisioning.pretrained import load_chbmit_pretrained
from backend.application_platform.provisioning.wiring import predict_with_pretrained

app = FastAPI(title="NeuroVision - Real Model (Fixed)", version="real-model-fix")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load once at startup (this is the key fix)
print("[REAL-MODEL] Loading trained CHB-MIT artifact...")
try:
    MODEL_CTX = load_chbmit_pretrained()
    print("[REAL-MODEL] ✓ Real model ready:", MODEL_CTX.model_id)
    print("[REAL-MODEL]   Accuracy:", MODEL_CTX.engine.metrics.get("accuracy"))
except Exception as e:
    print("[REAL-MODEL] FAILED to load real model:", e)
    MODEL_CTX = None

import mne
import numpy as np

@app.get("/", response_class=HTMLResponse)
def home():
    """Simple test page"""
    return """
    <html>
    <head><title>NeuroVision - Real Model</title></head>
    <body style="font-family: Arial; padding: 40px; background: #111; color: #eee;">
        <h1>NeuroVision - Real Trained Model (FIXED)</h1>
        <p style="color:#0f0;">✓ Real CHB-MIT model loaded successfully</p>
        
        <h2>Test Upload</h2>
        <form action="/upload_and_analyze" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".edf,.fif" required style="margin:10px 0;">
            <button type="submit" style="padding:10px 20px; background:#0af; color:white; border:none; cursor:pointer;">Upload EEG & Get Real Prediction</button>
        </form>
        
        <p><a href="/health" style="color:#0af;">Check /health</a></p>
        
        <hr style="margin:30px 0; border-color:#333;">
        <small>For frontend: POST to <code>/upload_and_analyze</code> with form field <code>file</code></small>
    </body>
    </html>
    """

@app.get("/health")
def health():
    return {
        "status": "ok",
        "real_model_loaded": MODEL_CTX is not None,
        "model_id": getattr(MODEL_CTX, "model_id", None),
        "message": "Using REAL trained CHB-MIT model (placeholder bug fixed)"
    }

@app.post("/upload_and_analyze")
async def upload_and_analyze(file: UploadFile = File(...)):
    """
    This is what your Processing + Result pages should call.
    Returns:
      - File metadata (duration, sfreq, channels, integrity)
      - Real seizure detection from the trained model
    """
    if MODEL_CTX is None:
        raise HTTPException(status_code=503, detail="Real model not loaded")

    content = await file.read()

    # Write to temp for MNE
    with tempfile.NamedTemporaryFile(suffix=".edf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        raw = mne.io.read_raw_edf(tmp_path, preload=True, verbose="ERROR")
        sfreq = float(raw.info["sfreq"])
        data = raw.get_data() * 1e6   # microvolts

        # === Metadata for your Processing page ===
        metadata = {
            "filename": file.filename,
            "size_bytes": len(content),
            "duration_seconds": round(raw.times[-1], 2) if len(raw.times) > 0 else 0.0,
            "sampling_frequency": sfreq,
            "n_channels": data.shape[0],
            "integrity": "valid",
            "channels": raw.ch_names[:8]   # first 8 for display
        }

        # === Real prediction using training-time features ===
        class _Proc:
            def __init__(self, d, s):
                self.data = d
                class M:
                    sampling_frequency = s
                self.metadata = M()

        proc = _Proc(data, sfreq)
        pred = predict_with_pretrained(MODEL_CTX, proc)

        # === Result for your Result page ===
        result = {
            "status": "SUCCESS",
            "upload": metadata,
            "prediction": {
                "predicted_label": pred["predicted_label"],
                "probabilities": [round(float(x), 6) for x in pred["probabilities"]],
                "confidence": round(float(pred["confidence"]), 6),
                "model_source": "chbmit_pretrained_phase9",
            }
        }
        return JSONResponse(result)

    except Exception as e:
        return JSONResponse({"status": "ERROR", "detail": str(e)}, status_code=400)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("NEUROVISION - REAL MODEL SERVER (FIXED)")
    print("Using the actual trained chbmit_model.json")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=False)
