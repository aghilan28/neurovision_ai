"""Final validation for Productization P5 — Clinical Inference Foundation.

Objectively verifies the directive's 15 phase-completion criteria: that a trained model
(P4) + a feature asset (P3) can be executed into a validated prediction asset
(prediction + confidence + calibration + explanation), registered, audited, and traced
(Patient -> ... -> Model -> Prediction), with determinism + prediction traceability
preserved, the test suite green, and repository boundaries intact.

    python -m scripts.verify_productization_p5
"""

from __future__ import annotations

import _repo_bootstrap  # noqa: F401

import pathlib
import subprocess
import sys
import tempfile

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "tests"))

    import _eeg_fixtures as fx
    from ml.lineage import LineageTracker
    from backend.clinical_cases import CaseService
    from backend.eeg_foundation import EEGFoundationService, LocalEEGStore
    from backend.signal_processing import SignalProcessingService, ProcessedSignalStore
    from backend.feature_engineering import FeatureEngineeringService
    from backend.model_foundation import ModelFoundationService, ModelArchitecture
    from backend.inference_foundation import (
        InferenceFoundationService, ModelExecutionEngine, ModelExecutionError, InferenceStatus,
        ConfidenceLevel, CalibrationQuality, ExplanationMethod,
    )

    tmp = tempfile.mkdtemp(prefix="nv_inf_p5_")
    fixtures = fx.generate_fixtures(str(pathlib.Path(tmp) / "fixtures"))

    tracker = LineageTracker()
    cases = CaseService(lineage_tracker=tracker)
    es = LocalEEGStore(str(pathlib.Path(tmp) / "raw"))
    esvc = EEGFoundationService(es, lineage_tracker=tracker)
    ps = ProcessedSignalStore(str(pathlib.Path(tmp) / "proc"))
    ssvc = SignalProcessingService(es, ps, lineage_tracker=tracker)
    fsvc = FeatureEngineeringService(ps, lineage_tracker=tracker)
    names = [fx.VALID_EDF, fx.VALID_EDF_PLUS, fx.VALID_BDF, fx.VALID_BDF_PLUS, fx.VALID_FIF, fx.VALID_SET]
    feats = []
    for i, name in enumerate(names):
        c = cases.create_case(patient_key=f"P-{i}", case_key=f"C-{i}")
        raw = esvc.ingest_eeg(fixtures[name], case_id=c.case_id, patient_id=c.patient_id,
                              case_lineage_id=c.lineage_id).asset
        feats.append(fsvc.generate_features(ssvc.process(raw).asset).asset)

    mf = ModelFoundationService(lineage_tracker=tracker)
    model = mf.train_model(feats, architecture=ModelArchitecture.EEGNET, dataset_key="cohort", seed=7).model
    inf = InferenceFoundationService(lineage_tracker=tracker)

    # --- 1. model execution works ---
    try:
        eng = ModelExecutionEngine()
        fitted, meta, bundle = eng.load_model(model, feats, dataset_key="cohort")
        verified = meta["params_fingerprint_verified"] and meta["version_verified"]
        failed = False
        try:
            import dataclasses
            eng.load_model(dataclasses.replace(model, params_fingerprint="0" * 16), feats,
                           dataset_key="cohort")
        except ModelExecutionError:
            failed = True
        check("1. Model execution works", verified and failed,
              f"verified={verified} tamper_rejected={failed}")
    except Exception as exc:
        check("1. Model execution works", False, f"error: {exc}")

    out = inf.predict(model, feats[0], train_feature_records=feats, dataset_key="cohort")
    asset = out.asset

    # --- 2. predictions generate ---
    try:
        probs = asset.prediction.probabilities
        ok = (out.accepted and abs(sum(probs) - 1.0) < 1e-6
              and asset.prediction.predicted_class == int(np.argmax(probs)))
        check("2. Predictions generate", ok,
              f"predicted_class={asset.prediction.predicted_class} prob_sum={round(sum(probs), 6)}")
    except Exception as exc:
        check("2. Predictions generate", False, f"error: {exc}")

    # --- 3. confidence scoring works ---
    try:
        c = asset.confidence
        ok = (0.0 <= c.confidence_score <= 1.0 and 0.0 <= c.prediction_stability <= 1.0
              and c.confidence_level == ConfidenceLevel.from_score(c.prediction_reliability))
        check("3. Confidence scoring works", ok,
              f"score={c.confidence_score:.2f} level={c.confidence_level.value}")
    except Exception as exc:
        check("3. Confidence scoring works", False, f"error: {exc}")

    # --- 4. calibration works ---
    try:
        cal = asset.calibration
        ok = (0.0 <= cal.expected_calibration_error <= 1.0 and cal.brier_score >= 0.0
              and cal.calibration_quality == CalibrationQuality.from_ece(cal.expected_calibration_error))
        check("4. Calibration works", ok,
              f"ece={cal.expected_calibration_error:.3f} quality={cal.calibration_quality.value}")
    except Exception as exc:
        check("4. Calibration works", False, f"error: {exc}")

    # --- 5. explainability works ---
    try:
        e = asset.explanation
        ok = (e.method == ExplanationMethod.OCCLUSION and len(e.feature_contributions) == 29
              and set(e.band_importance) == {"delta", "theta", "alpha", "beta", "gamma"}
              and len(e.channel_importance) >= 1 and len(e.decision_factors) > 0)
        check("5. Explainability works", ok, "feature/band/channel importance + decision factors")
    except Exception as exc:
        check("5. Explainability works", False, f"error: {exc}")

    # --- 6. prediction assets generate ---
    try:
        ok = (asset is not None and asset.status == InferenceStatus.GENERATED
              and asset.prediction is not None and asset.confidence is not None
              and asset.calibration is not None and asset.explanation is not None)
        check("6. Prediction assets generate", ok, f"status={asset.status.value}")
    except Exception as exc:
        check("6. Prediction assets generate", False, f"error: {exc}")

    # --- 7. registry works ---
    try:
        ok = (inf.registry.exists(asset.prediction_id)
              and asset.prediction_id in inf.registry.by_model(asset.model_id)
              and asset.prediction_id in inf.registry.by_feature(asset.feature_asset_id))
        check("7. Registry works", ok, f"n_predictions={len(inf.registry.list_predictions())}")
    except Exception as exc:
        check("7. Registry works", False, f"error: {exc}")

    # --- 8. validation works (9 checks) ---
    try:
        report = inf.integrity(asset)
        ok = (asset.validation.ok and report.ok and report.to_dict()["n_checks"] == 9)
        check("8. Validation works", ok,
              f"content_ok={asset.validation.ok} integrity_ok={report.ok} n_checks={report.to_dict()['n_checks']}")
    except Exception as exc:
        check("8. Validation works", False, f"error: {exc}")

    # --- 9. audit integration works ---
    try:
        log = inf.audit_log_for(asset.prediction_id)
        kinds = {ev.kind for ev in log.events()}
        ok = (log.verify() and log.head == asset.audit_head
              and {"model_loaded", "prediction_generated", "confidence_assessed",
                   "calibration_assessed", "explanation_generated", "prediction_registered"} <= kinds)
        check("9. Audit integration works", ok, f"events={len(log)} verified={log.verify()}")
    except Exception as exc:
        check("9. Audit integration works", False, f"error: {exc}")

    # --- 10. lineage integration works ---
    try:
        kinds = {r.kind for r in tracker.chain(asset.lineage_id)}
        ok = tracker.verify_chain(asset.lineage_id) and {
            "patient", "case", "eeg", "processed_eeg", "feature", "dataset", "training_run",
            "model", "prediction"} <= kinds
        check("10. Lineage integration works", ok, f"kinds={sorted(kinds)}")
    except Exception as exc:
        check("10. Lineage integration works", False, f"error: {exc}")

    # --- 11. reports generate ---
    try:
        reports = inf.reports(asset)
        expected = {"prediction_report", "confidence_report", "calibration_report",
                    "explainability_report", "inference_report", "registry_report", "audit_report",
                    "lineage_report", "validation_report"}
        ok = (set(reports) == expected and reports == inf.reports(asset)
              and reports["validation_report"]["ok"] is True)
        check("11. Reports generate", ok, f"reports={len(reports)}")
    except Exception as exc:
        check("11. Reports generate", False, f"error: {exc}")

    # --- 14. determinism preserved ---
    try:
        b = inf.predict(model, feats[0], train_feature_records=feats, dataset_key="cohort").asset
        ok = (asset.prediction_id == b.prediction_id and asset.version.version == b.version.version
              and asset.prediction.signature() == b.prediction.signature())
        check("14. Determinism preserved", ok, "re-inference reproduces id/version/prediction")
    except Exception as exc:
        check("14. Determinism preserved", False, f"error: {exc}")

    # --- 15. prediction traceability preserved ---
    try:
        node = tracker.get(asset.lineage_id)
        kinds = {r.kind for r in tracker.chain(asset.lineage_id)}
        ok = (model.lineage_id in node.parents and feats[0].lineage_id in node.parents
              and {"patient", "model", "prediction"} <= kinds)
        check("15. Prediction traceability preserved", ok, "prediction -> model + input feature")
    except Exception as exc:
        check("15. Prediction traceability preserved", False, f"error: {exc}")

    # --- 12. tests pass ---
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "tests/test_inference_foundation.py", "tests/test_inference_foundation_e2e.py"],
            cwd=str(REPO), capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("12. Tests pass", proc.returncode == 0, tail)
    except Exception as exc:
        check("12. Tests pass", False, f"error: {exc}")

    # --- 13. repository boundaries preserved ---
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_boundaries.py"],
            cwd=str(REPO), capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("13. Repository boundaries preserved", proc.returncode == 0, tail)
    except Exception as exc:
        check("13. Repository boundaries preserved", False, f"error: {exc}")

    # --- report (ordered 1..15) ---
    order = {f"{i}.": i for i in range(1, 16)}
    checks.sort(key=lambda c: order.get(c[0].split(" ")[0], 99))
    print("\nPRODUCTIZATION P5 — CLINICAL INFERENCE FOUNDATION — FINAL VALIDATION")
    print("=" * 68)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 68)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
