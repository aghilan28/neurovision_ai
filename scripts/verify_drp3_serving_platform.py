"""Final validation for DRP-3 — Production Serving Platform.

Verifies the directive's 15 criteria against the real subsystem, driving the **real**
P1->P3 feature pipeline + model-foundation training + the reused inference foundation over
the committed EEG fixtures (no replacement systems), and serving predictions for every
architecture.

    python -m scripts.verify_drp3_serving_platform
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]


def _cohort(tmp: pathlib.Path):
    sys.path.insert(0, str(REPO / "tests"))
    from _eeg_fixtures import generate_fixtures
    from _drp3_helpers import build_feature_cohort
    eeg = generate_fixtures(str(tmp / "fix"))
    return build_feature_cohort(eeg, tmp)


def main() -> int:
    checks: list[tuple] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "tests"))
    from backend.model_foundation import ModelArchitecture
    from backend.serving_platform import (
        ServingPlatformService, PredictionRequestContract, ServingStatus, ReadinessClass,
    )
    from _drp3_helpers import train_model

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="drp3_verify_"))
    tracker, feats = _cohort(tmp)
    svc = ServingPlatformService(lineage_tracker=tracker)

    outs = {}
    for arch in ModelArchitecture:
        model = train_model(tracker, feats, architecture=arch)
        svc.load_model(model, feats, dataset_key="cohort")
        req = PredictionRequestContract(
            model_ref={"model_id": model.model_id}, feature_asset_id=feats[0].feature_asset_id,
            case_id=feats[0].case_id, patient_id=feats[0].patient_id)
        outs[arch.value] = svc.serve(req, feats[0])
    rep = next(iter(outs.values()))

    # --- 1. model serving works ---
    try:
        ok = all(o.accepted and svc.engine.is_loaded(o.execution.model_id) for o in outs.values())
        check("1. Model serving works", ok and len(outs) == len(ModelArchitecture),
              f"served={sorted(outs)}")
    except Exception as exc:
        check("1. Model serving works", False, f"error: {exc}")

    # --- 2. prediction serving works ---
    try:
        ok = all(o.execution.response.confidence_level and o.execution.response.calibration_quality
                 and len(o.execution.response.probability_scores) > 0
                 and len(o.execution.response.explanation_summary) > 0 for o in outs.values())
        check("2. Prediction serving works", ok, "prediction + confidence + calibration + explanation")
    except Exception as exc:
        check("2. Prediction serving works", False, f"error: {exc}")

    # --- 3. contracts work ---
    try:
        rc = rep.response_contract
        ok = (rc["contract"] == "PredictionResponse" and "prediction" in rc and "confidence" in rc
              and "calibration" in rc and "explanation" in rc)
        check("3. Contracts work", ok, f"contract_version={rc.get('contract_version')}")
    except Exception as exc:
        check("3. Contracts work", False, f"error: {exc}")

    # --- 4. validation works ---
    try:
        ok = all(svc.integrity(o.execution).ok for o in outs.values())
        check("4. Validation works", ok, "content + integrity validation pass for every execution")
    except Exception as exc:
        check("4. Validation works", False, f"error: {exc}")

    # --- 5. registry works ---
    try:
        counts = svc.registry.counts()
        ok = (all(svc.registry.exists(o.execution.execution_id) for o in outs.values())
              and svc.registry.orphans() == []
              and counts["serving_execution"] == len(outs))
        check("5. Registry works", ok, f"counts={counts} orphans={len(svc.registry.orphans())}")
    except Exception as exc:
        check("5. Registry works", False, f"error: {exc}")

    # --- 6. readiness works ---
    try:
        classes = sorted({o.readiness.classification.value for o in outs.values()})
        ok = all(o.readiness.classification == ReadinessClass.READY for o in outs.values())
        check("6. Readiness works", ok, f"classes={classes}")
    except Exception as exc:
        check("6. Readiness works", False, f"error: {exc}")

    # --- 7. audit integration works ---
    try:
        log = svc.audit_log_for(rep.execution.execution_id)
        ok = log.verify() and rep.execution.audit_head == log.head and len(log) >= 7
        check("7. Audit integration works", ok, f"events={len(log)} verified={log.verify()}")
    except Exception as exc:
        check("7. Audit integration works", False, f"error: {exc}")

    # --- 8. lineage integration works ---
    try:
        kinds = {n.kind for n in tracker.chain(rep.execution.response.lineage_id)}
        required = {"patient", "case", "eeg", "processed_eeg", "feature", "dataset", "training_run",
                    "model", "prediction", "serving_request", "serving_execution", "serving_response"}
        ok = required <= kinds and tracker.verify_chain(rep.execution.response.lineage_id)
        check("8. Lineage integration works", ok, f"kinds>={sorted(required)}")
    except Exception as exc:
        check("8. Lineage integration works", False, f"error: {exc}")

    # --- 9. reports generate ---
    try:
        reports = svc.reports(rep.execution)
        expected = {"serving_report", "execution_report", "validation_report", "readiness_report",
                    "registry_report", "audit_report", "lineage_report", "contract_report",
                    "service_summary_report"}
        check("9. Reports generate", expected == set(reports), f"reports={len(reports)}")
    except Exception as exc:
        check("9. Reports generate", False, f"error: {exc}")

    # --- 12. determinism preserved (cross-instance) ---
    try:
        tmp2 = pathlib.Path(tempfile.mkdtemp(prefix="drp3_verify2_"))
        tracker2, feats2 = _cohort(tmp2)
        svc2 = ServingPlatformService(lineage_tracker=tracker2)
        model2 = train_model(tracker2, feats2, architecture=ModelArchitecture.EEGNET)
        svc2.load_model(model2, feats2, dataset_key="cohort")
        req2 = PredictionRequestContract(model_ref={"model_id": model2.model_id},
                                         feature_asset_id=feats2[0].feature_asset_id,
                                         case_id=feats2[0].case_id, patient_id=feats2[0].patient_id)
        e2 = svc2.serve(req2, feats2[0]).execution
        e1 = outs["eegnet"].execution
        ok = e1.execution_id == e2.execution_id and e1.version.version == e2.version.version
        check("12. Determinism preserved", ok, "same execution id + version across instances")
    except Exception as exc:
        check("12. Determinism preserved", False, f"error: {exc}")

    # --- 13. serving traceability preserved ---
    try:
        ok = all(tracker.verify_chain(o.execution.response.lineage_id) for o in outs.values())
        check("13. Serving traceability preserved", ok,
              "every served response chain reaches the patient")
    except Exception as exc:
        check("13. Serving traceability preserved", False, f"error: {exc}")

    # --- 14. serving readiness works ---
    try:
        ok = all(0.0 <= o.readiness.score <= 1.0 and len(o.readiness.dimensions) == 6
                 for o in outs.values())
        check("14. Serving readiness works", ok,
              f"scores={sorted({o.readiness.score for o in outs.values()})}")
    except Exception as exc:
        check("14. Serving readiness works", False, f"error: {exc}")

    # --- 15. production serving platform completed ---
    try:
        ok = (len(outs) == len(ModelArchitecture)
              and all(o.accepted and o.reason == ServingStatus.COMPLETED.value
                      and o.readiness.classification == ReadinessClass.READY for o in outs.values()))
        check("15. Production serving platform completed", ok,
              "all architectures served: request -> select -> infer -> respond -> trace -> audit")
    except Exception as exc:
        check("15. Production serving platform completed", False, f"error: {exc}")

    # --- 10. tests pass ---
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               "tests/test_serving_platform.py",
                               "tests/test_serving_platform_e2e.py"], cwd=str(REPO),
                              capture_output=True, text=True)
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
    print("\nDRP-3 — PRODUCTION SERVING PLATFORM — FINAL VALIDATION")
    print("=" * 64)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 64)
    print("ARCHITECTURES:",
          ", ".join(f"{a}={outs[a].readiness.classification.value}" for a in sorted(outs)))
    print("-" * 64)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
