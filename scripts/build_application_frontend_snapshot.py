"""Build the Application Frontend snapshot (Productization P7).

Drives the full user journey (register -> login -> upload -> analyse -> view
prediction -> view reports) through the **real** backend via the live gateway, renders
every page to deterministic static HTML, and serializes the frontend reports + rendered
HTML into a snapshot. This is a composition seam (scripts may import both layers); the
frontend itself imports no domain module (NR-8).

    python -m scripts.build_application_frontend_snapshot --out app_frontend_snapshot.json
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import tempfile
from typing import Optional

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from backend.application_backend import DeterministicEntropy  # noqa: E402
from frontend.application_frontend import FrontendValidator, reporting  # noqa: E402
from scripts.application_frontend_gateway import build_live_app  # noqa: E402

SNAPSHOT_VERSION = "application-frontend-snapshot@1.0.0"

_FIXTURE_NAMES = ["valid.edf", "valid_edf_plus.edf", "valid.bdf", "valid_bdf_plus.bdf",
                  "valid_raw.fif", "valid.set"]


def _cohort(fixtures: dict) -> list:
    return [(f"P-{i}", f"C-{i}", fixtures[n]) for i, n in enumerate(_FIXTURE_NAMES)]


def build_snapshot(*, workspace_dir: Optional[str] = None) -> dict:
    import _eeg_fixtures as fx

    tmp = workspace_dir or tempfile.mkdtemp(prefix="nv_p7_snap_")
    fixtures = fx.generate_fixtures(str(pathlib.Path(tmp) / "fixtures"))
    svc, gw, app = build_live_app(_cohort(fixtures), workspace_dir=str(pathlib.Path(tmp) / "ws"),
                                  entropy=DeterministicEntropy("snapshot"))

    # The full user journey through the real backend.
    app.register("dr.demo", "password123", "password123", "clinician")
    app.login("dr.demo", "password123")
    app.dashboard()
    with open(fixtures["valid.edf"], "rb") as fh:
        content = fh.read()
    upload = app.upload("demo_recording.edf", content)
    upload_id = upload.data["upload"]["upload_id"]
    analysis = app.start_analysis(upload_id)
    analysis_id = analysis.data["workflow"]["analysis_id"]

    validation = FrontendValidator().validate(app, analysis_id=analysis_id)
    reports = reporting.build_all_reports(app, validation_report=validation,
                                          operations_exercised=gw.call_log)

    rendered = {
        "login": app.render_login(), "register": app.render_register(),
        "dashboard": app.render_dashboard(), "upload": app.render_upload(),
        "analysis": app.render_analysis(), "prediction": app.render_prediction(analysis_id),
        "reports": app.render_reports(analysis_id),
    }
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "source": "real backend driven through the live gateway (scripts seam)",
        "analysis_id": analysis_id, "upload_id": upload_id,
        "frontend_validation_ok": validation.ok,
        "operations_exercised": sorted(set(gw.call_log)),
        "reports": reports,
        "state": app.state.snapshot(),
        "rendered_pages": rendered,
    }


def write_snapshot(out_path: str) -> str:
    snapshot = build_snapshot()
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, sort_keys=True, separators=(",", ":"))
    return out_path


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description="Build the Application Frontend snapshot (P7).")
    p.add_argument("--out", default="app_frontend_snapshot.json")
    args = p.parse_args(argv)
    path = write_snapshot(args.out)
    snap = build_snapshot()
    print(f"wrote {path}")
    print(f"snapshot_version       : {snap['snapshot_version']}")
    print(f"frontend validation ok : {snap['frontend_validation_ok']}")
    print(f"operations exercised   : {len(snap['operations_exercised'])}/12")
    print(f"pages rendered         : {len(snap['rendered_pages'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
