"""Final validation for Track 3 — Real Product Application Program.

Verifies the directive's 15 criteria against the **real** Application Platform: a real
FastAPI HTTP API (driven via ``TestClient``) over a **real** EEG file and a **real** model
prepared from the locally-acquired CHB-MIT corpus (acquired by Track 1 if missing — network
on first run, reused locally thereafter). It proves a complete user workflow end-to-end —
register -> login -> upload real EEG -> predict -> report (JSON/HTML/PDF) -> READY_FOR_USERS
— using real recordings and real trained models, not synthetic fixtures.

    python -m scripts.verify_track3_application

Set NV_TRACK1_NO_DOWNLOAD=1 to forbid network (then the corpus must already be local).
"""

from __future__ import annotations

import base64
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    checks: list[tuple] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "tests"))

    from fastapi.testclient import TestClient

    from backend.application_platform import (
        ApplicationPlatformService, ApplicationReadinessClass, EntityKind, create_app,
    )
    from backend.application_platform.uploads import prepare_bounded_segment
    from backend.dataset_acquisition import DatasetSource, RealDatasetService
    from backend.model_foundation import ModelArchitecture

    # --- ensure the real CHB-MIT corpus is present (acquire if missing) ------
    allow_download = os.environ.get("NV_TRACK1_NO_DOWNLOAD") not in ("1", "true", "True")
    ds_svc = RealDatasetService()
    ds_svc.acquire(DatasetSource.CHB_MIT, allow_download=allow_download, timeout=300.0)
    out = ds_svc.integrate(DatasetSource.CHB_MIT, allow_download=False)
    recs = [(r.relative_path) for r in out.connector_result.recordings if r.parse_ok]
    real_files = [ds_svc.storage.abspath(DatasetSource.CHB_MIT, r) for r in recs]

    analysis_seconds = 20.0
    svc = ApplicationPlatformService(analysis_seconds=analysis_seconds)

    # prepare a real model from bounded segments of the genuine recordings
    segs, cohort = [], []
    for i, fpath in enumerate(real_files[:2]):
        with open(fpath, "rb") as fh:
            seg, _fp, _sz = prepare_bounded_segment(fh.read(), os.path.basename(fpath),
                                                    analysis_seconds=analysis_seconds)
        segs.append(seg)
        cohort.append((f"p{i}", f"c{i}", seg))
    try:
        svc.prepare_model(cohort, architecture=ModelArchitecture.EEGNET)
    finally:
        for s in segs:
            if os.path.exists(s):
                os.remove(s)

    app = create_app(svc)
    client = TestClient(app)

    # --- run the real user workflow over the real EEG ------------------------
    client.post("/v1/auth/register", json={"username": "clinician",
                                           "password": "pw-123456", "roles": ["clinician"]})
    token = client.post("/v1/auth/login",
                        json={"username": "clinician", "password": "pw-123456"}).json()["token"]
    hdr = {"Authorization": f"Bearer {token}"}
    with open(real_files[-1], "rb") as fh:
        content = fh.read()
    up = client.post("/v1/uploads", json={"filename": os.path.basename(real_files[-1]),
                                          "content_base64": base64.b64encode(content).decode()},
                     headers=hdr)
    body = up.json()
    aid = body.get("analysis_id")
    outcome = svc.get_analysis(aid) if aid else None

    # --- 1. API works ---
    try:
        h = client.get("/health").json()
        ok = (h["status"] == "ok" and client.get("/v1/model/status").json()["prepared"]
              and "/v1/uploads" in client.get("/openapi.json").json()["paths"])
        check("1. API works", ok, f"FastAPI v{h['api_version']} health+status+openapi")
    except Exception as exc:
        check("1. API works", False, f"error: {exc}")

    # --- 2. upload workflow works ---
    try:
        ok = up.status_code == 201 and body["accepted"] and body["upload"]["status"] == "validated"
        check("2. Upload workflow works", ok,
              f"format={body['upload']['format']} n_channels={body['upload']['n_channels']}")
    except Exception as exc:
        check("2. Upload workflow works", False, f"error: {exc}")

    # --- 3. analysis workflow works ---
    try:
        ok = outcome is not None and outcome.workflow.status.value == "completed" and \
            len(outcome.workflow.stages) == 8
        check("3. Analysis workflow works", ok,
              f"stages={len(outcome.workflow.stages) if outcome else 0}")
    except Exception as exc:
        check("3. Analysis workflow works", False, f"error: {exc}")

    # --- 4. prediction workflow works ---
    try:
        pred = body["prediction"]
        pr = client.get(f"/v1/analyses/{aid}/prediction").json()
        ok = (bool(pred["predicted_label"] != "") and bool(pred["model_id"])
              and {"confidence", "calibration", "explanation", "model"} <= set(pr["evidence"]))
        check("4. Prediction workflow works", ok,
              f"label={pred['predicted_label']} conf={pred['confidence_level']} model={pred['model_id'][:18]}")
    except Exception as exc:
        check("4. Prediction workflow works", False, f"error: {exc}")

    # --- 5. reports generate (JSON/HTML/PDF) ---
    try:
        rj = client.get(f"/v1/analyses/{aid}/reports", params={"type": "analysis", "format": "json"})
        rh = client.get(f"/v1/analyses/{aid}/reports", params={"type": "prediction", "format": "html"})
        rp = client.get(f"/v1/analyses/{aid}/reports", params={"type": "evidence", "format": "pdf"})
        ok = (rj.status_code == 200 and rh.status_code == 200 and b"<html" in rh.content.lower()
              and rp.status_code == 200 and rp.content[:5] == b"%PDF-")
        check("5. Reports generate", ok, "JSON + HTML + PDF exported")
    except Exception as exc:
        check("5. Reports generate", False, f"error: {exc}")

    # --- 6. registry integration works ---
    try:
        counts = svc.registry.counts()
        ok = (svc.registry.orphans() == [] and counts[EntityKind.UPLOAD.value] >= 1
              and counts[EntityKind.PREDICTION_RESULT.value] >= 1
              and counts[EntityKind.REPORT.value] >= 1)
        check("6. Registry integration works", ok, f"counts={counts} orphans=0")
    except Exception as exc:
        check("6. Registry integration works", False, f"error: {exc}")

    # --- 7. audit integration works ---
    try:
        ok = svc.audit.verify() and len(svc.audit) >= 4
        check("7. Audit integration works", ok, f"events={len(svc.audit)} verified={svc.audit.verify()}")
    except Exception as exc:
        check("7. Audit integration works", False, f"error: {exc}")

    # --- 8. lineage integration works ---
    try:
        node = outcome.report_record.lineage_id
        kinds = {n.kind for n in svc.lineage.chain(node)}
        required = {"app_upload", "app_model_ref", "app_prediction_request",
                    "app_prediction_result", "app_report"}
        ok = required <= kinds and svc.lineage.verify_chain(node)
        check("8. Lineage integration works", ok, f"chain={sorted(kinds)}")
    except Exception as exc:
        check("8. Lineage integration works", False, f"error: {exc}")

    # --- 9. readiness scoring works ---
    try:
        rclass = body["readiness"]["classification"]
        ok = rclass == ApplicationReadinessClass.READY_FOR_USERS.value
        check("9. Readiness scoring works", ok,
              f"classification={rclass} score={body['readiness']['score']}")
    except Exception as exc:
        check("9. Readiness scoring works", False, f"error: {exc}")

    # --- 12. determinism preserved ---
    try:
        svc2 = ApplicationPlatformService(analysis_seconds=analysis_seconds)
        segs2, cohort2 = [], []
        for i, fpath in enumerate(real_files[:2]):
            with open(fpath, "rb") as fh:
                seg, _fp, _sz = prepare_bounded_segment(fh.read(), os.path.basename(fpath),
                                                        analysis_seconds=analysis_seconds)
            segs2.append(seg)
            cohort2.append((f"p{i}", f"c{i}", seg))
        try:
            svc2.prepare_model(cohort2, architecture=ModelArchitecture.EEGNET)
        finally:
            for s in segs2:
                if os.path.exists(s):
                    os.remove(s)
        c2 = TestClient(create_app(svc2))
        c2.post("/v1/auth/register", json={"username": "clinician", "password": "pw-123456"})
        t2 = c2.post("/v1/auth/login",
                     json={"username": "clinician", "password": "pw-123456"}).json()["token"]
        b2 = c2.post("/v1/uploads", json={"filename": os.path.basename(real_files[-1]),
                                          "content_base64": base64.b64encode(content).decode()},
                     headers={"Authorization": f"Bearer {t2}"}).json()
        ok = (b2["analysis_id"] == aid
              and b2["prediction"]["prediction_result_id"] == body["prediction"]["prediction_result_id"])
        check("12. Determinism preserved", ok, "same analysis + prediction ids across instances")
    except Exception as exc:
        check("12. Determinism preserved", False, f"error: {exc}")

    # --- 13. user workflow exists ---
    try:
        ok = (body["accepted"] and aid and outcome.analysis.status.value == "completed")
        check("13. User workflow exists", ok, "register->login->upload->analyze->predict->report")
    except Exception as exc:
        check("13. User workflow exists", False, f"error: {exc}")

    # --- 14. real prediction workflow exists ---
    try:
        ok = (body["upload"]["n_channels"] >= 1 and body["upload"]["sampling_frequency"] > 0
              and body["prediction"]["model_id"] and body["prediction"]["predicted_label"] != "")
        check("14. Real prediction workflow exists", ok,
              f"real EEG {body['upload']['n_channels']}ch @ {body['upload']['sampling_frequency']}Hz -> prediction")
    except Exception as exc:
        check("14. Real prediction workflow exists", False, f"error: {exc}")

    # --- 15. Track 3 completed ---
    try:
        ok = (body["accepted"] and body["readiness"]["classification"] == "READY_FOR_USERS"
              and outcome.validation.ok and svc.lineage.verify_chain(outcome.report_record.lineage_id))
        check("15. Track 3 completed", ok,
              "real EEG uploaded -> prediction -> report -> READY_FOR_USERS, traceable")
    except Exception as exc:
        check("15. Track 3 completed", False, f"error: {exc}")

    # --- 10. tests pass ---
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "tests/test_application_platform.py", "tests/test_application_platform_e2e.py"],
            cwd=str(REPO), capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("10. Tests pass", proc.returncode == 0, tail)
    except Exception as exc:
        check("10. Tests pass", False, f"error: {exc}")

    # --- 11. repository boundaries preserved ---
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               "tests/test_boundaries.py"], cwd=str(REPO),
                              capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("11. Repository boundaries preserved", proc.returncode == 0, tail)
    except Exception as exc:
        check("11. Repository boundaries preserved", False, f"error: {exc}")

    order = {f"{i}.": i for i in range(1, 16)}
    checks.sort(key=lambda c: order.get(c[0].split(" ")[0], 99))
    print("\nTRACK 3 — REAL PRODUCT APPLICATION — FINAL VALIDATION")
    print("=" * 66)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 66)
    if outcome is not None:
        print(f"USER WORKFLOW: upload={body['upload']['filename']} "
              f"({body['upload']['n_channels']}ch@{body['upload']['sampling_frequency']}Hz) "
              f"-> predicted={body['prediction']['predicted_label']} "
              f"-> readiness={body['readiness']['classification']}")
    print("-" * 66)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
