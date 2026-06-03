"""NeuroVision Deployment Server.

Composes the NeuroVision UI with the real backend platform for production serving.
"""

from __future__ import annotations

import _repo_bootstrap  # noqa: F401
import os
import pathlib
import uvicorn
from fastapi import FastAPI, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from scripts.application_frontend_gateway import LiveBackendGateway
from backend.application_backend import ApplicationBackendService, DeterministicEntropy
from frontend.application_frontend import FrontendApp

REPO = pathlib.Path(__file__).resolve().parents[1]

# In production, the cohort should be provided via configuration or database.
# This bootstrap uses an empty cohort if no real data is provided.
cohort_dir = os.environ.get("NV_COHORT_DIR")
if cohort_dir and os.path.exists(cohort_dir):
    files = sorted([f for f in os.listdir(cohort_dir) if f.endswith(('.edf', '.bdf'))])
    # build_live_app expects (patient_key, case_key, file_path)
    # We need to ensure patient_keys are distinct to satisfy patient-disjointness if required
    cohort = [(f"patient_{i}", f"case_{i}", os.path.join(cohort_dir, f)) for i, f in enumerate(files)]
else:
    cohort = []

# Manual composition to allow resilient startup if cohort is insufficient (< 2 patients)
workspace_dir = os.environ.get("NV_WORKSPACE_DIR", "workspace")
svc = ApplicationBackendService(workspace_dir=workspace_dir, entropy=DeterministicEntropy("prod-server"))

if len(cohort) >= 2:
    svc.prepare_model(cohort)
else:
    # Skip model preparation to avoid startup failure during UI-only deployments or inspections.
    print(f"WARNING: Insufficient cohort data ({len(cohort)} recordings). Starting in UI-only Demo Mode.")

gateway = LiveBackendGateway(svc.api)
app_frontend = FrontendApp(gateway)

server = FastAPI(title="NeuroVision")

@server.get("/", response_class=HTMLResponse)
async def index():
    if not app_frontend.is_authenticated:
        return RedirectResponse(url="/login")
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
    port = int(os.environ.get("PORT", 3000))
    uvicorn.run(server, host="0.0.0.0", port=port)
