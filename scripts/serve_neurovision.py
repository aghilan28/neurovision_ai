"""NeuroVision Constitution Server.

Serves the NeuroVision Intelligence Operating Environment on localhost.
Connects the Constitution-compliant UI to the real backend platform.

Usage:
    python scripts/serve_neurovision.py
"""

from __future__ import annotations

import _repo_bootstrap  # noqa: F401
import pathlib
import uvicorn
from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from scripts.application_frontend_gateway import build_live_app
from backend.application_backend import DeterministicEntropy

REPO = pathlib.Path(__file__).resolve().parents[1]

# Initialize the live app with dummy cohort for testing
cohort = [
    ("P-001", "C-001", "tests/data/valid1.edf"),
    ("P-002", "C-002", "tests/data/valid2.edf")
]
# Ensure dummy files exist for bootstrap
pathlib.Path("tests/data").mkdir(parents=True, exist_ok=True)
for _, _, path in cohort:
    if not pathlib.Path(path).exists():
        with open(path, "wb") as f:
            f.write(b"dummy eeg content")

svc, gateway, app_frontend = build_live_app(cohort, workspace_dir="workspace_dev",
                                          entropy=DeterministicEntropy("dev-server"))

# Auto-login a default user for convenience
app_frontend.register("operator", "neurovision123", "neurovision123", "clinician")
app_frontend.login("operator", "neurovision123")

server = FastAPI(title="NeuroVision Development Server")

@server.get("/", response_class=HTMLResponse)
async def index():
    return RedirectResponse(url="/dashboard")

@server.get("/{page}", response_class=HTMLResponse)
async def render_page(page: str, analysis_id: str = None):
    if page == "dashboard":
        return app_frontend.render_dashboard()
    elif page == "upload":
        return app_frontend.render_upload()
    elif page == "analysis":
        return app_frontend.render_analysis()
    elif page == "prediction":
        return app_frontend.render_prediction(analysis_id)
    elif page == "reports":
        return app_frontend.render_reports(analysis_id)
    elif page == "login":
        return app_frontend.render_login()
    elif page == "register":
        return app_frontend.render_register()
    return app_frontend.render_current()

@server.post("/action/upload")
async def handle_upload(file: UploadFile = File(...)):
    content = await file.read()
    app_frontend.upload(file.filename, content)
    return RedirectResponse(url="/upload", status_code=303)

@server.post("/action/analyze")
async def handle_analyze(upload_id: str = Form(...)):
    app_frontend.start_analysis(upload_id)
    return RedirectResponse(url="/analysis", status_code=303)

if __name__ == "__main__":
    print("\nNeuroVision Intelligence Operating Environment Starting...")
    print("Connecting to backend platform v1...")
    print("URL: http://localhost:3000")
    uvicorn.run(server, host="0.0.0.0", port=3000)
