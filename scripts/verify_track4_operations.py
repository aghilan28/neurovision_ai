"""Final validation for Track 4 — Operational Readiness & Deployment Qualification.

Verifies the directive's 15 criteria against the **real** Operations Platform qualifying the
**real** Track-3 product: it prepares a real model from the locally-acquired CHB-MIT corpus
(acquired by Track 1 if missing — network on first run, reused locally thereafter), runs a
real EEG through the real FastAPI workflow, then qualifies operations end-to-end and proves
the system is objectively ``READY_FOR_DEPLOYMENT`` — using the existing application platform,
real recordings, and real trained models.

    python -m scripts.verify_track4_operations

Set NV_TRACK1_NO_DOWNLOAD=1 to forbid network (then the corpus must already be local).
"""

from __future__ import annotations

import _repo_bootstrap  # noqa: F401

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

    from backend.application_platform import ApplicationPlatformService, create_app
    from backend.application_platform.uploads import prepare_bounded_segment
    from backend.dataset_acquisition import DatasetSource, RealDatasetService
    from backend.model_foundation import ModelArchitecture
    from backend.operations_platform import (
        DeploymentReadinessClass, EntityKind, HealthState, OperationsPlatformService,
        QualificationStatus,
    )

    # --- ensure the real corpus is present, build a real Track-3 product -----
    allow_download = os.environ.get("NV_TRACK1_NO_DOWNLOAD") not in ("1", "true", "True")
    ds_svc = RealDatasetService()
    ds_svc.acquire(DatasetSource.CHB_MIT, allow_download=allow_download, timeout=300.0)
    t1 = ds_svc.integrate(DatasetSource.CHB_MIT, allow_download=False)
    real_files = [ds_svc.storage.abspath(DatasetSource.CHB_MIT, r.relative_path)
                  for r in t1.connector_result.recordings if r.parse_ok]

    analysis_seconds = 20.0
    product = ApplicationPlatformService(analysis_seconds=analysis_seconds)
    segs, cohort = [], []
    for i, fpath in enumerate(real_files[:2]):
        with open(fpath, "rb") as fh:
            seg, _fp, _sz = prepare_bounded_segment(fh.read(), os.path.basename(fpath),
                                                    analysis_seconds=analysis_seconds)
        segs.append(seg)
        cohort.append((f"p{i}", f"c{i}", seg))
    try:
        product.prepare_model(cohort, architecture=ModelArchitecture.EEGNET)
    finally:
        for s in segs:
            if os.path.exists(s):
                os.remove(s)

    client = TestClient(create_app(product))
    client.post("/v1/auth/register", json={"username": "clinician", "password": "pw-123456"})
    token = client.post("/v1/auth/login",
                        json={"username": "clinician", "password": "pw-123456"}).json()["token"]
    with open(real_files[-1], "rb") as fh:
        content = fh.read()
    client.post("/v1/uploads", json={"filename": os.path.basename(real_files[-1]),
                                     "content_base64": base64.b64encode(content).decode()},
                headers={"Authorization": f"Bearer {token}"})

    # --- Track 4: qualify operations -----------------------------------------
    ops = OperationsPlatformService(product)
    out = ops.qualify()

    # --- 1. health monitoring works ---
    try:
        ok = out.health.overall == HealthState.HEALTHY and out.health.n_components == 7
        check("1. Health monitoring works", ok,
              f"overall={out.health.overall.value} components={out.health.n_components}")
    except Exception as exc:
        check("1. Health monitoring works", False, f"error: {exc}")

    # --- 2. monitoring works ---
    try:
        m = out.metrics.deterministic_metrics
        ok = m["request_volume"] >= 1 and m["prediction_volume"] >= 1 and m["upload_volume"] >= 1
        check("2. Monitoring works", ok, f"metrics={m}")
    except Exception as exc:
        check("2. Monitoring works", False, f"error: {exc}")

    # --- 3. diagnostics work ---
    try:
        ok = out.diagnostic.ok and out.diagnostic.n_findings >= 5
        check("3. Diagnostics work", ok,
              f"ok={out.diagnostic.ok} findings={out.diagnostic.n_findings} "
              f"root_causes={list(out.diagnostic.root_causes)}")
    except Exception as exc:
        check("3. Diagnostics work", False, f"error: {exc}")

    # --- 4. qualification works ---
    try:
        ok = (out.qualification.status == QualificationStatus.QUALIFIED
              and out.qualification.n_available == out.qualification.n_targets == 7)
        check("4. Qualification works", ok,
              f"status={out.qualification.status.value} "
              f"available={out.qualification.n_available}/{out.qualification.n_targets}")
    except Exception as exc:
        check("4. Qualification works", False, f"error: {exc}")

    # --- 5. readiness scoring works ---
    try:
        ok = (out.readiness.classification == DeploymentReadinessClass.READY_FOR_DEPLOYMENT
              and out.readiness.score >= 0.999)
        check("5. Readiness scoring works", ok,
              f"classification={out.readiness.classification.value} score={out.readiness.score}")
    except Exception as exc:
        check("5. Readiness scoring works", False, f"error: {exc}")

    # --- 6. registry integration works ---
    try:
        counts = ops.registry.counts()
        ok = (ops.registry.orphans() == [] and counts[EntityKind.HEALTH_CHECK.value] == 1
              and counts[EntityKind.QUALIFICATION.value] == 1
              and counts[EntityKind.READINESS.value] == 1)
        check("6. Registry integration works", ok, f"counts={counts} orphans=0")
    except Exception as exc:
        check("6. Registry integration works", False, f"error: {exc}")

    # --- 7. audit integration works ---
    try:
        ok = ops.audit.verify() and len(ops.audit) >= 5
        check("7. Audit integration works", ok, f"events={len(ops.audit)} verified={ops.audit.verify()}")
    except Exception as exc:
        check("7. Audit integration works", False, f"error: {exc}")

    # --- 8. lineage integration works ---
    try:
        kinds = {n.kind for n in ops.lineage.chain(out.readiness_lineage_id)}
        spine = {"ops_health_event", "ops_qualification_event", "ops_readiness"}
        product_chain = {"app_upload", "app_prediction_result", "app_report"}
        ok = (spine <= kinds and product_chain <= kinds
              and ops.lineage.verify_chain(out.readiness_lineage_id))
        check("8. Lineage integration works", ok, f"chain reaches product workflow ({len(kinds)} kinds)")
    except Exception as exc:
        check("8. Lineage integration works", False, f"error: {exc}")

    # --- 9. reports generate ---
    try:
        reports = ops.reports(out)
        expected = {"health_report", "monitoring_report", "diagnostics_report",
                    "qualification_report", "readiness_report", "audit_report", "lineage_report",
                    "operational_summary_report"}
        check("9. Reports generate", expected == set(reports), f"reports={len(reports)}")
    except Exception as exc:
        check("9. Reports generate", False, f"error: {exc}")

    # --- 12. determinism preserved ---
    try:
        product2 = ApplicationPlatformService(analysis_seconds=analysis_seconds)
        segs2, cohort2 = [], []
        for i, fpath in enumerate(real_files[:2]):
            with open(fpath, "rb") as fh:
                seg, _fp, _sz = prepare_bounded_segment(fh.read(), os.path.basename(fpath),
                                                        analysis_seconds=analysis_seconds)
            segs2.append(seg)
            cohort2.append((f"p{i}", f"c{i}", seg))
        try:
            product2.prepare_model(cohort2, architecture=ModelArchitecture.EEGNET)
        finally:
            for s in segs2:
                if os.path.exists(s):
                    os.remove(s)
        c2 = TestClient(create_app(product2))
        c2.post("/v1/auth/register", json={"username": "clinician", "password": "pw-123456"})
        t2 = c2.post("/v1/auth/login",
                     json={"username": "clinician", "password": "pw-123456"}).json()["token"]
        c2.post("/v1/uploads", json={"filename": os.path.basename(real_files[-1]),
                                     "content_base64": base64.b64encode(content).decode()},
                headers={"Authorization": f"Bearer {t2}"})
        out2 = OperationsPlatformService(product2).qualify()
        ok = (out.readiness.readiness_id == out2.readiness.readiness_id
              and out.qualification.qualification_id == out2.qualification.qualification_id
              and out.health.health_check_id == out2.health.health_check_id)
        check("12. Determinism preserved", ok, "same health/qualification/readiness ids")
    except Exception as exc:
        check("12. Determinism preserved", False, f"error: {exc}")

    # --- 13. operational qualification exists ---
    try:
        ok = (out.health.overall == HealthState.HEALTHY and out.diagnostic.ok
              and bool(out.metrics.deterministic_metrics))
        check("13. Operational qualification exists", ok,
              "health + monitoring + diagnostics over the real product")
    except Exception as exc:
        check("13. Operational qualification exists", False, f"error: {exc}")

    # --- 14. deployment qualification exists ---
    try:
        ok = out.qualification.status == QualificationStatus.QUALIFIED and out.ready_for_deployment
        check("14. Deployment qualification exists", ok,
              f"qualification={out.qualification.status.value}")
    except Exception as exc:
        check("14. Deployment qualification exists", False, f"error: {exc}")

    # --- 15. Track 4 completed ---
    try:
        ok = (out.ready_for_deployment
              and out.readiness.classification == DeploymentReadinessClass.READY_FOR_DEPLOYMENT
              and ops.lineage.verify_chain(out.readiness_lineage_id) and ops.audit.verify())
        check("15. Track 4 completed", ok,
              "health -> monitor -> diagnose -> qualify -> READY_FOR_DEPLOYMENT, traceable")
    except Exception as exc:
        check("15. Track 4 completed", False, f"error: {exc}")

    # --- 10. tests pass ---
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "tests/test_operations_platform.py"],
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
    print("\nTRACK 4 — OPERATIONAL READINESS & DEPLOYMENT QUALIFICATION — FINAL VALIDATION")
    print("=" * 74)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 74)
    print(f"OPERATIONAL QUALIFICATION: health={out.health.overall.value} "
          f"qualification={out.qualification.status.value} "
          f"readiness={out.readiness.classification.value} score={out.readiness.score}")
    print("-" * 74)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
