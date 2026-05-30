"""Final validation for Productization P1 — Real EEG Foundation Layer.

Objectively verifies the directive's 15 phase-completion criteria: that real EEG
files of every supported format (EDF/EDF+/BDF/BDF+/FIF/SET) can enter the platform
and be loaded, validated, parsed, have metadata extracted, be stored, registered,
audited, lineage-tracked (Patient -> Case -> EEG), and reported on — with the full
test suite green and repository boundaries preserved.

Exits non-zero if any criterion fails.

    python -m scripts.verify_productization_p1
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
    from backend.eeg_foundation import (
        EEGFoundationService, LocalEEGStore, EEGFileValidator, EEGFormat,
        EEGAssetStatus, load_eeg, detect_format,
    )

    tmp = tempfile.mkdtemp(prefix="nv_eeg_p1_")
    fixtures = fx.generate_fixtures(str(pathlib.Path(tmp) / "fixtures"))

    # Build the platform: one shared lineage tracker, a Case, an EEG service.
    tracker = LineageTracker()
    case = CaseService(lineage_tracker=tracker).create_case(patient_key="P-VP1", case_key="C-VP1")
    svc = EEGFoundationService(LocalEEGStore(str(pathlib.Path(tmp) / "store")),
                               lineage_tracker=tracker)

    def ingest(name):
        return svc.ingest_eeg(fixtures[name], case_id=case.case_id,
                              patient_id=case.patient_id, case_lineage_id=case.lineage_id)

    # --- 1-6: each supported format is read and registered from a real file ---
    fmt_fixture = [
        ("1. EDF support works", fx.VALID_EDF, EEGFormat.EDF),
        ("2. EDF+ support works", fx.VALID_EDF_PLUS, EEGFormat.EDF_PLUS),
        ("3. BDF support works", fx.VALID_BDF, EEGFormat.BDF),
        ("4. BDF+ support works", fx.VALID_BDF_PLUS, EEGFormat.BDF_PLUS),
        ("5. FIF support works", fx.VALID_FIF, EEGFormat.FIF),
        ("6. SET support works", fx.VALID_SET, EEGFormat.SET),
    ]
    assets = {}
    for label, name, expected in fmt_fixture:
        try:
            detected, _ = detect_format(fixtures[name])
            out = ingest(name)
            ok = (detected == expected and out.accepted
                  and out.asset.eeg_format == expected
                  and out.asset.status == EEGAssetStatus.REGISTERED
                  and out.asset.channel_set.count == 3)
            assets[name] = out.asset
            check(label, ok, f"detected={detected.value if detected else None} "
                             f"status={out.asset.status.value if out.asset else None}")
        except Exception as exc:  # pragma: no cover - defensive
            check(label, False, f"error: {exc}")

    edf = assets.get(fx.VALID_EDF)
    edf_plus = assets.get(fx.VALID_EDF_PLUS)

    # --- 7: metadata extraction works (deterministic) ---
    try:
        m1 = load_eeg(fixtures[fx.VALID_EDF_PLUS])
        from backend.eeg_foundation import extract_metadata
        md_a = extract_metadata(m1)
        md_b = extract_metadata(load_eeg(fixtures[fx.VALID_EDF_PLUS]))
        ok = (md_a.to_dict() == md_b.to_dict() and md_a.n_channels == 3
              and md_a.sampling_frequency == 256.0 and md_a.n_annotations == 2
              and md_a.recording_id.startswith("recording+"))
        check("7. Metadata extraction works", ok,
              f"recording_id={md_a.recording_id} ann={md_a.n_annotations}")
    except Exception as exc:
        check("7. Metadata extraction works", False, f"error: {exc}")

    # --- 8: validation works (structured findings; corrupted + unsupported) ---
    try:
        v = EEGFileValidator()
        ok_valid = v.validate_path(fixtures[fx.VALID_EDF])[1].ok is True
        corrupt = v.validate_path(fixtures[fx.CORRUPTED_EDF])[1]
        unsupported = v.validate_path(fixtures[fx.UNSUPPORTED])[1]
        ok = (ok_valid and corrupt.has_errors
              and {f.code for f in corrupt.findings} >= {"corrupted_file"}
              and {f.code for f in unsupported.findings} == {"unsupported_format"})
        check("8. Validation works", ok,
              f"valid_ok={ok_valid} corrupted={[f.code for f in corrupt.findings]} "
              f"unsupported={[f.code for f in unsupported.findings]}")
    except Exception as exc:
        check("8. Validation works", False, f"error: {exc}")

    # --- 9: registry works (no orphans) ---
    try:
        ok = (svc.registry.exists(edf.asset_id)
              and edf.asset_id in svc.registry.by_case(case.case_id)
              and len(svc.registry.list_assets()) == len(assets))
        check("9. Registry works", ok, f"n_assets={len(svc.registry.list_assets())}")
    except Exception as exc:
        check("9. Registry works", False, f"error: {exc}")

    # --- 10: storage works (content-addressed + integrity) ---
    try:
        ok = (svc.store.exists(edf.storage) and svc.store.verify(edf.storage)
              and edf.storage.checksum_sha256 and edf.storage.content_fingerprint
              and edf.storage.file_size_bytes > 0)
        check("10. Storage works", ok,
              f"verify={svc.store.verify(edf.storage)} ref={edf.storage.raw_file_reference}")
    except Exception as exc:
        check("10. Storage works", False, f"error: {exc}")

    # --- 11: audit integration works (shared immutable log, tamper-evident) ---
    try:
        log = svc.audit_log_for(edf.asset_id)
        kinds = {e.kind for e in log.events()}
        ok = (log.verify() and log.head == edf.audit_head
              and {"eeg_ingested", "eeg_validated", "eeg_stored",
                   "eeg_lineage_recorded", "eeg_registered"} <= kinds)
        check("11. Audit integration works", ok, f"events={len(log)} verified={log.verify()}")
    except Exception as exc:
        check("11. Audit integration works", False, f"error: {exc}")

    # --- 12: lineage integration works (Patient -> Case -> EEG) ---
    try:
        ok = True
        for a in assets.values():
            kinds = {r.kind for r in tracker.chain(a.lineage_id)}
            ok = ok and tracker.verify_chain(a.lineage_id) and {"patient", "case", "eeg"} <= kinds
        check("12. Lineage integration works", ok, "every asset verifies Patient -> Case -> EEG")
    except Exception as exc:
        check("12. Lineage integration works", False, f"error: {exc}")

    # --- 13: reports generate (deterministic) ---
    try:
        reports = svc.reports(edf_plus)
        expected = {"eeg_summary_report", "eeg_metadata_report", "eeg_validation_report",
                    "eeg_audit_report", "eeg_lineage_report", "eeg_registry_report"}
        ok = (set(reports) == expected and reports == svc.reports(edf_plus)
              and reports["eeg_lineage_report"]["chain_verified"] is True)
        check("13. Reports generate", ok, f"reports={sorted(reports)}")
    except Exception as exc:
        check("13. Reports generate", False, f"error: {exc}")

    # --- 14: tests pass (the EEG suite) ---
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "tests/test_eeg_foundation.py", "tests/test_eeg_foundation_e2e.py"],
            cwd=str(REPO), capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("14. Tests pass", proc.returncode == 0, tail)
    except Exception as exc:
        check("14. Tests pass", False, f"error: {exc}")

    # --- 15: repository boundaries preserved ---
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "tests/test_boundaries.py"],
            cwd=str(REPO), capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("15. Repository boundaries preserved", proc.returncode == 0, tail)
    except Exception as exc:
        check("15. Repository boundaries preserved", False, f"error: {exc}")

    # --- report ---
    print("\nPRODUCTIZATION P1 — REAL EEG FOUNDATION — FINAL VALIDATION")
    print("=" * 64)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        tag = "PASS" if ok else "FAIL"
        line = f"[{tag}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 64)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
