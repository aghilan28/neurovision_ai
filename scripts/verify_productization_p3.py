"""Final validation for Productization P3 — Feature Engineering Platform.

Objectively verifies the directive's 15 phase-completion criteria: that a processed
EEG asset (from P2) can have frequency / temporal / connectivity / spectral /
topography features generated into an immutable, validated, registered, audited,
lineage-tracked feature asset (Patient -> Case -> EEG -> Processed -> Feature), with
determinism + traceability preserved, the test suite green, and boundaries intact.

    python -m scripts.verify_productization_p3
"""

from __future__ import annotations

import _repo_bootstrap  # noqa: F401

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
    from backend.feature_engineering import (
        FeatureEngineeringService, FrequencyFeatureEngine, TemporalFeatureEngine,
        ConnectivityFeatureEngine, SpectralRepresentationEngine, TopographyRepresentationEngine,
        FeatureFamily, FeatureAssetStatus, load_processed_signal,
    )
    from backend.feature_engineering._common import REGION_NAMES

    tmp = tempfile.mkdtemp(prefix="nv_feat_p3_")
    fixtures = fx.generate_fixtures(str(pathlib.Path(tmp) / "fixtures"))

    tracker = LineageTracker()
    case = CaseService(lineage_tracker=tracker).create_case(patient_key="P-VP3", case_key="C-VP3")
    eeg_store = LocalEEGStore(str(pathlib.Path(tmp) / "raw"))
    eeg_svc = EEGFoundationService(eeg_store, lineage_tracker=tracker)
    proc_store = ProcessedSignalStore(str(pathlib.Path(tmp) / "proc"))
    sig_svc = SignalProcessingService(eeg_store, proc_store, lineage_tracker=tracker)
    feat_svc = FeatureEngineeringService(proc_store, lineage_tracker=tracker)

    raw = eeg_svc.ingest_eeg(fixtures[fx.VALID_FIF], case_id=case.case_id,
                             patient_id=case.patient_id, case_lineage_id=case.lineage_id).asset
    processed = sig_svc.process(raw).asset
    data, sfreq, ch = load_processed_signal(proc_store, processed)

    # --- 1. frequency features ---
    try:
        names = {v.name for v in FrequencyFeatureEngine().extract(data, sfreq, ch)}
        ok = ({f"abs_power_{b}" for b in ("delta", "theta", "alpha", "beta", "gamma")} <= names
              and {"absolute_power", "spectral_entropy", "rel_power_alpha"} <= names)
        check("1. Frequency features work", ok, f"n={len(names)}")
    except Exception as exc:
        check("1. Frequency features work", False, f"error: {exc}")

    # --- 2. temporal features ---
    try:
        names = {v.name for v in TemporalFeatureEngine().extract(data, sfreq, ch)}
        ok = {"mean", "variance", "skewness", "kurtosis", "rms", "zero_crossing_rate",
              "hjorth_activity", "hjorth_mobility", "hjorth_complexity", "signal_entropy"} <= names
        check("2. Temporal features work", ok, f"n={len(names)}")
    except Exception as exc:
        check("2. Temporal features work", False, f"error: {exc}")

    # --- 3. connectivity features ---
    try:
        import numpy as np
        v = {x.name: x for x in ConnectivityFeatureEngine().extract(data, sfreq, ch)}
        n = data.shape[0]
        m = np.array(v["coherence_matrix"].values).reshape(n, n)
        ok = (v["coherence_matrix"].shape == (n, n) and np.allclose(np.diag(m), 1.0)
              and "plv_matrix" in v and "cross_correlation_matrix" in v and "synchronization" in v)
        check("3. Connectivity features work", ok, f"matrices for {n} channels")
    except Exception as exc:
        check("3. Connectivity features work", False, f"error: {exc}")

    # --- 4. spectral representations ---
    try:
        v = {x.name: x for x in SpectralRepresentationEngine().extract(data, sfreq, ch)}
        ok = ("psd" in v and len(v["spectrogram"].shape) == 3 and v["band_summary"].n_values == 5
              and "frequency_histogram" in v)
        check("4. Spectral representations work", ok,
              f"psd shape={v['psd'].shape} spec shape={v['spectrogram'].shape}")
    except Exception as exc:
        check("4. Spectral representations work", False, f"error: {exc}")

    # --- 5. topography representations ---
    try:
        v = {x.name: x for x in TopographyRepresentationEngine().extract(data, sfreq, ch)}
        ok = (v["channel_layout"].n_values == data.shape[0]
              and v["regional_rms"].n_values == len(REGION_NAMES)
              and "spatial_summary" in v and "topographic_stat" in v)
        check("5. Topography representations work", ok, "structured (no images)")
    except Exception as exc:
        check("5. Topography representations work", False, f"error: {exc}")

    # --- 6. feature assets generate ---
    outcome = feat_svc.generate_features(processed)
    asset = outcome.asset
    try:
        ok = (outcome.accepted and asset is not None
              and asset.status == FeatureAssetStatus.GENERATED
              and set(asset.families) == {f.value for f in FeatureFamily} and len(asset.vectors) > 0)
        check("6. Feature assets generate", ok,
              f"families={len(asset.families)} vectors={len(asset.vectors)}")
    except Exception as exc:
        check("6. Feature assets generate", False, f"error: {exc}")

    # --- 7. registry works ---
    try:
        ok = (feat_svc.registry.exists(asset.feature_asset_id)
              and asset.feature_asset_id in feat_svc.registry.by_processed(processed.processed_id)
              and asset.feature_asset_id in feat_svc.registry.by_family("frequency"))
        check("7. Registry works", ok, f"n_assets={len(feat_svc.registry.list_assets())}")
    except Exception as exc:
        check("7. Registry works", False, f"error: {exc}")

    # --- 8. audit integration works ---
    try:
        log = feat_svc.audit_log_for(asset.feature_asset_id)
        kinds = {e.kind for e in log.events()}
        ok = (log.verify() and log.head == asset.audit_head
              and {"features_extracted", "features_validated", "feature_lineage_recorded",
                   "feature_version_changed", "feature_registered"} <= kinds)
        check("8. Audit integration works", ok, f"events={len(log)} verified={log.verify()}")
    except Exception as exc:
        check("8. Audit integration works", False, f"error: {exc}")

    # --- 9. lineage integration works ---
    try:
        kinds = {r.kind for r in tracker.chain(asset.lineage_id)}
        ok = tracker.verify_chain(asset.lineage_id) and {
            "patient", "case", "eeg", "processed_eeg", "feature"} <= kinds
        check("9. Lineage integration works", ok, f"kinds={sorted(kinds)}")
    except Exception as exc:
        check("9. Lineage integration works", False, f"error: {exc}")

    # --- 10. validation works (content + integrity, 8 checks) ---
    try:
        report = feat_svc.integrity(asset)
        ok = (asset.validation.ok and report.ok and report.to_dict()["n_checks"] == 8)
        check("10. Validation works", ok,
              f"content_ok={asset.validation.ok} integrity_ok={report.ok} n_checks={report.to_dict()['n_checks']}")
    except Exception as exc:
        check("10. Validation works", False, f"error: {exc}")

    # --- 11. reports generate ---
    try:
        reports = feat_svc.reports(asset)
        expected = {"frequency_report", "temporal_report", "connectivity_report", "spectral_report",
                    "topography_report", "registry_report", "audit_report", "lineage_report",
                    "validation_report"}
        ok = (set(reports) == expected and reports == feat_svc.reports(asset)
              and reports["validation_report"]["ok"] is True)
        check("11. Reports generate", ok, f"reports={len(reports)}")
    except Exception as exc:
        check("11. Reports generate", False, f"error: {exc}")

    # --- 14. determinism preserved ---
    try:
        b = feat_svc.generate_features(processed).asset
        det = next(c for c in asset.validation.checks if c[0] == "feature_determinism")
        ok = (asset.feature_asset_id == b.feature_asset_id and asset.version.version == b.version.version
              and bool(det[1]))
        check("14. Determinism preserved", ok, "re-generation reproduces id/version + determinism check")
    except Exception as exc:
        check("14. Determinism preserved", False, f"error: {exc}")

    # --- 15. feature traceability preserved ---
    try:
        report = feat_svc.integrity(asset)
        lineage_ok = next(c for c in report.checks if c.name == "lineage_integrity").passed \
            if hasattr(report, "checks") else True
        kinds = {r.kind for r in tracker.chain(asset.lineage_id)}
        ok = (tracker.verify_chain(asset.lineage_id)
              and {"patient", "case", "eeg", "processed_eeg", "feature"} <= kinds and lineage_ok)
        check("15. Feature traceability preserved", ok, "chain Patient -> ... -> Feature verifies")
    except Exception as exc:
        check("15. Feature traceability preserved", False, f"error: {exc}")

    # --- 12. tests pass ---
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "tests/test_feature_engineering.py", "tests/test_feature_engineering_e2e.py"],
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
    print("\nPRODUCTIZATION P3 — FEATURE ENGINEERING PLATFORM — FINAL VALIDATION")
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
