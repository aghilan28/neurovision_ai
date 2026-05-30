"""Final validation for Productization P4 — Model Foundation Platform.

Objectively verifies the directive's 15 phase-completion criteria: that feature assets
(from P3) can be assembled into a patient-disjoint dataset, used to train + evaluate +
track + register validated models (Patient -> ... -> Dataset -> Training Run -> Model),
with determinism + training/model traceability preserved, the test suite green, and
repository boundaries intact.

    python -m scripts.verify_productization_p4
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

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
    from backend.model_foundation import (
        ModelFoundationService, ModelArchitecture, DatasetSource, DatasetStatus,
        ExternalDatasetConnector, build_feature_dataset, train, evaluate,
    )

    tmp = tempfile.mkdtemp(prefix="nv_model_p4_")
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

    # --- 1. dataset framework works (external connectors; no download) ---
    try:
        rec = ExternalDatasetConnector(DatasetSource.TUH_EEG).build_record(
            {"name": "TUH", "n_recordings": 9, "patients": ["a", "b"], "channels": ["Fp1"],
             "sampling_frequency": 256}, dataset_key="tuh")
        bad = ExternalDatasetConnector(DatasetSource.CHB_MIT).build_record({"name": "x"}, dataset_key="k")
        ok = (rec.status == DatasetStatus.REGISTERED and rec.source_metadata["downloaded"] is False
              and bad.status == DatasetStatus.QUARANTINED)
        check("1. Dataset framework works", ok, "TUH/CHB-MIT/Temple connectors; manifest-only")
    except Exception as exc:
        check("1. Dataset framework works", False, f"error: {exc}")

    # --- 2. dataset registry works ---
    try:
        bundle = build_feature_dataset(feats, name="d", dataset_key="k", seed=7)
        ext = mf.register_external_dataset(DatasetSource.TUH_EEG, {
            "name": "TUH", "n_recordings": 9, "patients": ["a"], "channels": ["Fp1"],
            "sampling_frequency": 256}, dataset_key="tuh")
        ok = (bundle.X.shape[1] == 29 and bundle.record.split.patient_disjoint
              and mf.dataset_registry.exists(ext.dataset_id))
        check("2. Dataset registry works", ok,
              f"feature_dataset n={bundle.X.shape[0]}x{bundle.X.shape[1]} disjoint")
    except Exception as exc:
        check("2. Dataset registry works", False, f"error: {exc}")

    # --- 3. training works ---
    try:
        run, model = train(ModelArchitecture.EEGNET, bundle, n_classes=2, seed=7)
        run2, _ = train(ModelArchitecture.EEGNET, bundle, n_classes=2, seed=7)
        ok = (run.n_params > 0 and run.params_fingerprint == run2.params_fingerprint
              and 0.0 <= run.training_metrics["train_accuracy"] <= 1.0)
        check("3. Training works", ok, f"n_params={run.n_params} deterministic")
    except Exception as exc:
        check("3. Training works", False, f"error: {exc}")

    # --- 4. evaluation works ---
    try:
        ev = evaluate(model, bundle, training_run_id=run.training_run_id, n_classes=2)
        ok = (0.0 <= ev.metrics["accuracy"] <= 1.0 and len(ev.confusion_matrix) == 2
              and {"ece", "brier"} <= set(ev.calibration)
              and {"mean_entropy", "mean_confidence"} <= set(ev.uncertainty))
        check("4. Evaluation works", ok, f"acc={ev.metrics['accuracy']:.2f} +calibration+uncertainty")
    except Exception as exc:
        check("4. Evaluation works", False, f"error: {exc}")

    # --- train models via the service (drives 5-15) ---
    models = {}
    for arch in ModelArchitecture:
        models[arch] = mf.train_model(feats, architecture=arch, name=f"exp-{arch.value}",
                                      dataset_key="cohort", seed=7).model
    model = models[ModelArchitecture.EEGNET]

    # --- 5. experiment tracking works ---
    try:
        ok = mf.experiment_registry.exists(model.experiment_id)
        exp = mf.experiment_registry.get(model.experiment_id)
        ok = ok and exp.training_run_id == model.training_run_id and model.model_id in exp.artifact_refs
        check("5. Experiment tracking works", ok,
              f"experiments={len(mf.experiment_registry.list_experiments())}")
    except Exception as exc:
        check("5. Experiment tracking works", False, f"error: {exc}")

    # --- 6. model registry works ---
    try:
        ok = (mf.model_registry.exists(model.model_id)
              and len(mf.model_registry.list_models()) == len(list(ModelArchitecture))
              and model.model_id in mf.model_registry.by_dataset(model.dataset_id))
        check("6. Model registry works", ok, f"models={len(mf.model_registry.list_models())}")
    except Exception as exc:
        check("6. Model registry works", False, f"error: {exc}")

    # --- 7. validation works (9 checks) ---
    try:
        report = mf.integrity(model)
        ok = (model.validation.ok and report.ok and report.to_dict()["n_checks"] == 9)
        check("7. Validation works", ok,
              f"content_ok={model.validation.ok} integrity_ok={report.ok} n_checks={report.to_dict()['n_checks']}")
    except Exception as exc:
        check("7. Validation works", False, f"error: {exc}")

    # --- 8. audit integration works ---
    try:
        log = mf.audit_log_for(model.model_id)
        kinds = {e.kind for e in log.events()}
        ok = (log.verify() and log.head == model.audit_head
              and {"dataset_registered", "training_completed", "evaluation_completed",
                   "experiment_tracked", "model_registered"} <= kinds)
        check("8. Audit integration works", ok, f"events={len(log)} verified={log.verify()}")
    except Exception as exc:
        check("8. Audit integration works", False, f"error: {exc}")

    # --- 9. lineage integration works ---
    try:
        kinds = {r.kind for r in tracker.chain(model.lineage_id)}
        ok = tracker.verify_chain(model.lineage_id) and {
            "patient", "case", "eeg", "processed_eeg", "feature", "dataset",
            "training_run", "model"} <= kinds
        check("9. Lineage integration works", ok, f"kinds={sorted(kinds)}")
    except Exception as exc:
        check("9. Lineage integration works", False, f"error: {exc}")

    # --- 10. reports generate ---
    try:
        reports = mf.reports(model)
        expected = {"dataset_report", "training_report", "evaluation_report", "experiment_report",
                    "model_report", "registry_report", "audit_report", "lineage_report",
                    "validation_report"}
        ok = (set(reports) == expected and reports == mf.reports(model)
              and reports["validation_report"]["ok"] is True)
        check("10. Reports generate", ok, f"reports={len(reports)}")
    except Exception as exc:
        check("10. Reports generate", False, f"error: {exc}")

    # --- 13. determinism preserved ---
    try:
        a = mf.train_model(feats, architecture=ModelArchitecture.DEEPCONVNET, dataset_key="cohort",
                           seed=7).model
        b = mf.train_model(feats, architecture=ModelArchitecture.DEEPCONVNET, dataset_key="cohort",
                           seed=7).model
        ok = (a.model_id == b.model_id and a.version.version == b.version.version
              and a.params_fingerprint == b.params_fingerprint)
        check("13. Determinism preserved", ok, "re-training reproduces id/version/params")
    except Exception as exc:
        check("13. Determinism preserved", False, f"error: {exc}")

    # --- 14. training traceability preserved ---
    try:
        tr_kind = tracker.get(tracker.get(model.lineage_id).parents[0]).kind
        ds_node = mf.dataset_registry.get(model.dataset_id).lineage_id
        ok = (tr_kind == "training_run" and ds_node and tracker.verify_chain(ds_node))
        check("14. Training traceability preserved", ok, "model -> training_run -> dataset")
    except Exception as exc:
        check("14. Training traceability preserved", False, f"error: {exc}")

    # --- 15. model traceability preserved ---
    try:
        kinds = {r.kind for r in tracker.chain(model.lineage_id)}
        ok = (tracker.verify_chain(model.lineage_id)
              and {"patient", "case", "eeg", "processed_eeg", "feature", "dataset",
                   "training_run", "model"} <= kinds)
        check("15. Model traceability preserved", ok, "chain Patient -> ... -> Model verifies")
    except Exception as exc:
        check("15. Model traceability preserved", False, f"error: {exc}")

    # --- 11. tests pass ---
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "tests/test_model_foundation.py", "tests/test_model_foundation_e2e.py"],
            cwd=str(REPO), capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("11. Tests pass", proc.returncode == 0, tail)
    except Exception as exc:
        check("11. Tests pass", False, f"error: {exc}")

    # --- 12. repository boundaries preserved ---
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_boundaries.py"],
            cwd=str(REPO), capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("12. Repository boundaries preserved", proc.returncode == 0, tail)
    except Exception as exc:
        check("12. Repository boundaries preserved", False, f"error: {exc}")

    # --- report (ordered 1..15) ---
    order = {f"{i}.": i for i in range(1, 16)}
    checks.sort(key=lambda c: order.get(c[0].split(" ")[0], 99))
    print("\nPRODUCTIZATION P4 — MODEL FOUNDATION PLATFORM — FINAL VALIDATION")
    print("=" * 66)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 66)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
