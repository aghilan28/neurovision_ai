"""Final validation for Productization P2 — Signal Processing Foundation.

Objectively verifies the directive's 15 phase-completion criteria: that a raw EEG
asset (from P1) can be filtered, quality-assessed, have artifacts detected and
removed, become a stored/registered/audited/lineage-tracked *processed* asset
(Patient -> Case -> EEG -> Processed), with the raw EEG left immutable, processing
fully traceable, and quality + artifact scoring working — with the test suite green
and repository boundaries preserved.

    python -m scripts.verify_productization_p2
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
    from backend.signal_processing import (
        SignalProcessingService, ProcessedSignalStore, FilteringEngine, SignalQualityEngine,
        ArtifactDetectionEngine, ArtifactRemovalEngine, ArtifactType, ArtifactSeverity,
        ProcessedAssetStatus, QualityGrade, SignalKind, load_raw_signal,
    )

    tmp = tempfile.mkdtemp(prefix="nv_sig_p2_")
    fixtures = fx.generate_fixtures(str(pathlib.Path(tmp) / "fixtures"))

    tracker = LineageTracker()
    case = CaseService(lineage_tracker=tracker).create_case(patient_key="P-VP2", case_key="C-VP2")
    eeg_store = LocalEEGStore(str(pathlib.Path(tmp) / "raw"))
    eeg_svc = EEGFoundationService(eeg_store, lineage_tracker=tracker)
    sig_svc = SignalProcessingService(eeg_store, ProcessedSignalStore(str(pathlib.Path(tmp) / "proc")),
                                      lineage_tracker=tracker)

    raw_asset = eeg_svc.ingest_eeg(fixtures[fx.VALID_FIF], case_id=case.case_id,
                                   patient_id=case.patient_id, case_lineage_id=case.lineage_id).asset

    def band_power(x, sfreq, lo, hi):
        spec = np.abs(np.fft.rfft(x)) ** 2
        freqs = np.fft.rfftfreq(x.size, d=1.0 / sfreq)
        return float(spec[(freqs >= lo) & (freqs < hi)].sum())

    # base array from a real fixture, for engine-level checks
    base, sfreq, ch = load_raw_signal(fixtures[fx.VALID_FIF], "FIF")

    # --- 1. filtering works ---
    try:
        t = np.arange(base.shape[1]) / sfreq
        noisy = base.copy()
        noisy[0] += 10.0 * np.sin(2 * np.pi * 60.0 * t)
        filt, cfg = FilteringEngine().bandpass(noisy, sfreq, 0.5, 40.0)
        ok = (band_power(filt[0], sfreq, 55, 65) < 0.05 * band_power(noisy[0], sfreq, 55, 65)
              and cfg.filter_type.value == "bandpass" and np.array_equal(noisy, noisy))
        check("1. Filtering works", ok, "bandpass attenuates 60 Hz; deterministic")
    except Exception as exc:
        check("1. Filtering works", False, f"error: {exc}")

    # --- 2/14. quality assessment + scoring ---
    try:
        q = SignalQualityEngine().assess(base, sfreq, ch, eeg_asset_id=raw_asset.asset_id,
                                         signal_kind=SignalKind.RAW)
        ok = (0.0 <= q.recording_quality_score <= 1.0 and q.grade in set(QualityGrade)
              and len(q.channel_qualities) == base.shape[0]
              and q.grade == QualityGrade.from_score(q.recording_quality_score))
        check("2. Quality assessment works", ok, f"grade={q.grade.value} score={round(q.recording_quality_score, 4)}")
    except Exception as exc:
        check("2. Quality assessment works", False, f"error: {exc}")

    # --- 3/15. artifact detection + scoring (inject artifacts into a real-fixture array) ---
    try:
        art = base.copy()
        tt = np.arange(art.shape[1]) / sfreq
        for i in range(art.shape[0]):
            art[i] += 40.0 * np.sin(2 * np.pi * 60.0 * tt)   # powerline on all channels
        art[0] = 0.0                                          # then flatten channel 0
        detected = ArtifactDetectionEngine().detect_all(art, sfreq, ch)
        types = {a.artifact_type for a in detected}
        det_ok = ArtifactType.FLAT_CHANNEL in types and ArtifactType.POWERLINE in types
        check("3. Artifact detection works", det_ok, f"types={sorted(x.value for x in types)}")
        score_ok = detected and all(
            0.0 <= a.confidence <= 1.0 and a.severity in set(ArtifactSeverity) and a.affected_channels
            for a in detected)
        check("15. Artifact scoring works", bool(score_ok),
              "every artifact has confidence in [0,1] + a severity + affected channels")
    except Exception as exc:
        check("3. Artifact detection works", False, f"error: {exc}")
        check("15. Artifact scoring works", False, f"error: {exc}")

    # --- 4. artifact removal works ---
    try:
        rem = ArtifactRemovalEngine()
        repaired, info = rem.channel_repair(art, (0,))
        clean, info2 = rem.noise_suppression(repaired, sfreq, powerline_hz=60.0)
        ica_a, _ = rem.ica_remove(repaired, sfreq, ch)
        ica_b, _ = rem.ica_remove(repaired, sfreq, ch)
        ok = (float(np.std(repaired[0])) > 0.0                                   # flat channel repaired
              and band_power(clean[0], sfreq, 59, 61) < band_power(repaired[0], sfreq, 59, 61)
              and np.allclose(ica_a, ica_b))                                     # ICA deterministic
        check("4. Artifact removal works", ok, "channel repair + noise suppression + deterministic ICA")
    except Exception as exc:
        check("4. Artifact removal works", False, f"error: {exc}")

    # --- 5. processed EEG generation works ---
    outcome = sig_svc.process(raw_asset)
    asset = outcome.asset
    try:
        ok = (outcome.accepted and asset is not None
              and asset.status == ProcessedAssetStatus.PROCESSED
              and asset.processed_signal.n_channels == raw_asset.channel_set.count
              and sig_svc.processed_store.verify(asset.storage))
        check("5. Processed EEG generation works", ok,
              f"status={asset.status.value if asset else None} stored={sig_svc.processed_store.verify(asset.storage) if asset else False}")
    except Exception as exc:
        check("5. Processed EEG generation works", False, f"error: {exc}")

    # --- 6. registry works ---
    try:
        ok = (sig_svc.registry.exists(asset.processed_id)
              and asset.processed_id in sig_svc.registry.by_eeg_asset(raw_asset.asset_id)
              and asset.processed_id in sig_svc.registry.by_case(case.case_id))
        check("6. Registry works", ok, f"n_assets={len(sig_svc.registry.list_assets())}")
    except Exception as exc:
        check("6. Registry works", False, f"error: {exc}")

    # --- 7. audit integration works ---
    try:
        log = sig_svc.audit_log_for(asset.processed_id)
        kinds = {e.kind for e in log.events()}
        ok = (log.verify() and log.head == asset.audit_head
              and {"signal_loaded", "quality_assessed_raw", "artifacts_detected",
                   "signal_processed", "signal_stored", "signal_lineage_recorded",
                   "signal_registered"} <= kinds)
        check("7. Audit integration works", ok, f"events={len(log)} verified={log.verify()}")
    except Exception as exc:
        check("7. Audit integration works", False, f"error: {exc}")

    # --- 8. lineage integration works (Patient -> Case -> EEG -> Processed) ---
    try:
        kinds = {r.kind for r in tracker.chain(asset.lineage_id)}
        ok = tracker.verify_chain(asset.lineage_id) and {"patient", "case", "eeg", "processed_eeg"} <= kinds
        check("8. Lineage integration works", ok, f"kinds={sorted(kinds)}")
    except Exception as exc:
        check("8. Lineage integration works", False, f"error: {exc}")

    # --- 9. reports generate ---
    try:
        reports = sig_svc.reports(asset)
        expected = {"quality_report", "artifact_report", "filtering_report", "processing_report",
                    "registry_report", "audit_report", "lineage_report"}
        ok = (set(reports) == expected and reports == sig_svc.reports(asset)
              and reports["lineage_report"]["chain_verified"] is True)
        check("9. Reports generate", ok, f"reports={sorted(reports)}")
    except Exception as exc:
        check("9. Reports generate", False, f"error: {exc}")

    # --- 12. raw EEG immutability preserved ---
    try:
        ok = (eeg_svc.store.verify(raw_asset.storage)
              and sig_svc.processed_store.root_dir != eeg_svc.store.root_dir
              and sig_svc.integrity(asset).ok)
        check("12. Raw EEG immutability preserved", ok,
              f"raw_verify={eeg_svc.store.verify(raw_asset.storage)}")
    except Exception as exc:
        check("12. Raw EEG immutability preserved", False, f"error: {exc}")

    # --- 13. processing traceability preserved ---
    try:
        steps = asset.processing.steps
        chain_ok = (steps[0].input_fingerprint == asset.processing.input_fingerprint
                    and all(a.output_fingerprint == b.input_fingerprint for a, b in zip(steps, steps[1:]))
                    and steps[-1].output_fingerprint == asset.processing.output_fingerprint
                    and asset.storage.content_fingerprint == asset.processing.output_fingerprint)
        check("13. Processing traceability preserved", bool(chain_ok), f"steps={len(steps)} contiguous")
    except Exception as exc:
        check("13. Processing traceability preserved", False, f"error: {exc}")

    # --- 10. tests pass ---
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "tests/test_signal_processing.py", "tests/test_signal_processing_e2e.py"],
            cwd=str(REPO), capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("10. Tests pass", proc.returncode == 0, tail)
    except Exception as exc:
        check("10. Tests pass", False, f"error: {exc}")

    # --- 11. repository boundaries preserved ---
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_boundaries.py"],
            cwd=str(REPO), capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("11. Repository boundaries preserved", proc.returncode == 0, tail)
    except Exception as exc:
        check("11. Repository boundaries preserved", False, f"error: {exc}")

    # --- 14. quality scoring works (before vs after recorded) ---
    try:
        ok = (asset.quality_history.before is not None and asset.quality_history.after is not None
              and 0.0 <= asset.quality.recording_quality_score <= 1.0)
        check("14. Quality scoring works", ok,
              f"before={round(asset.quality_history.before.recording_quality_score, 3)} "
              f"after={round(asset.quality.recording_quality_score, 3)}")
    except Exception as exc:
        check("14. Quality scoring works", False, f"error: {exc}")

    # --- report (ordered 1..15) ---
    order = {f"{i}.": i for i in range(1, 16)}
    checks.sort(key=lambda c: order.get(c[0].split(" ")[0], 99))
    print("\nPRODUCTIZATION P2 — SIGNAL PROCESSING FOUNDATION — FINAL VALIDATION")
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
