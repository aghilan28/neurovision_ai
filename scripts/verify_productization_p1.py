"""Final validation for Productization P1 — Real EEG Foundation Layer.

Objectively verifies the directive's 15 criteria against real fixture files and prints
a PASS/FAIL line per criterion. Exits non-zero if any criterion fails.

    python -m scripts.verify_productization_p1
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
FX = REPO / "tests" / "fixtures" / "eeg"


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(FX))
    import generate  # fixture generator (in tests/fixtures/eeg)
    generate.generate_all(str(FX))

    from ml.lineage import LineageTracker
    from backend.clinical_cases import CaseService
    from backend.eeg_foundation import (
        EEGFoundationService, load_eeg, detect_format_path, EEGFormat, EEGValidator,
    )

    def fx(n):
        return str(FX / n)

    # one shared tracker + a case, so the chain is Patient -> Case -> EEG Asset
    tracker = LineageTracker()
    case = CaseService(lineage_tracker=tracker).create_case(patient_key="P1", case_key="C1")
    svc = EEGFoundationService(lineage_tracker=tracker)

    def ingest(name):
        return svc.ingest(fx(name), case=case)

    # 1-6: each format loads from real bytes + ingests to a valid registered asset
    fmt_files = [
        ("1. EDF support works", EEGFormat.EDF, "valid.edf"),
        ("2. EDF+ support works", EEGFormat.EDF_PLUS, "valid_plus.edf"),
        ("3. BDF support works", EEGFormat.BDF, "valid.bdf"),
        ("4. BDF+ support works", EEGFormat.BDF_PLUS, "valid_plus.bdf"),
        ("5. FIF support works", EEGFormat.FIF, "valid.fif"),
        ("6. SET support works", EEGFormat.SET, "valid.set"),
    ]
    records = {}
    for label, fmt, fname in fmt_files:
        raw = load_eeg(fx(fname))
        rec = ingest(fname)
        records[fmt] = rec
        ok = (raw.ok and raw.fmt == fmt and detect_format_path(fx(fname)) == _fam(fmt)
              and rec.fmt == fmt and rec.valid and rec.metadata.sampling_frequency > 0
              and rec.metadata.n_channels > 0)
        check(label, ok, f"fmt={raw.fmt} ok={raw.ok} valid={rec.valid}")

    edf_plus = records[EEGFormat.EDF_PLUS]
    set_rec = records[EEGFormat.SET]

    # 7. metadata extraction works
    check("7. Metadata extraction works",
          edf_plus.metadata.n_channels >= 1 and edf_plus.metadata.duration_seconds > 0
          and edf_plus.metadata.annotation_count == 2
          and edf_plus.metadata.recording_id == edf_plus.eeg_id
          and set_rec.metadata.sampling_frequency == 250.0)

    # 8. validation works (clean valid; corrupted + unsupported produce findings)
    v = EEGValidator()
    corrupt_edf = svc.ingest(fx("corrupted.edf"), case=case)
    corrupt_bdf = svc.ingest(fx("corrupted.bdf"), case=case)
    unsupported = v.validate(load_eeg(fx("unsupported.dat")))
    check("8. Validation works",
          records[EEGFormat.EDF].valid and (not corrupt_edf.valid)
          and "truncated_data" in {f["code"] for f in corrupt_edf.validation_summary["findings"]}
          and (not corrupt_bdf.valid) and (not unsupported.valid)
          and unsupported.max_severity == "critical")

    # 9. registry works (no orphans; lookups)
    check("9. Registry works",
          all(svc.registry.exists(r.eeg_id) for r in records.values())
          and records[EEGFormat.EDF].eeg_id in svc.registry.by_case(case.case_id)
          and len(svc.registry.list_assets()) >= 6)

    # 10. storage works (checksum + fingerprint + storage id + size)
    s = records[EEGFormat.EDF].storage
    check("10. Storage works",
          len(s.checksum_sha256) == 64 and s.storage_id.startswith("eegblob+")
          and s.file_size_bytes == os.path.getsize(fx("valid.edf")) and bool(s.fingerprint))

    # 11. audit integration works (shared immutable log; verifies; records events)
    from backend.clinical_cases.audit import ImmutableAuditLog
    kinds = {e.kind for e in svc.audit.events()}
    check("11. Audit integration works",
          isinstance(svc.audit, ImmutableAuditLog) and svc.audit.verify()
          and {"eeg_ingested", "eeg_validated", "eeg_stored", "eeg_registered"} <= kinds)

    # 12. lineage integration works (Patient -> Case -> EEG Asset; reaches patient)
    rec = records[EEGFormat.EDF]
    chain = {r.kind for r in tracker.chain(rec.lineage_id)}
    check("12. Lineage integration works",
          tracker.verify_chain(rec.lineage_id) and {"patient", "case", "eeg_asset"} <= chain)

    # 13. reports generate (deterministic)
    reports = svc.reports(edf_plus)
    check("13. Reports generate",
          {"eeg_summary_report", "eeg_validation_report", "eeg_metadata_report",
           "eeg_registry_report", "eeg_audit_report", "eeg_lineage_report"} <= set(reports)
          and reports["eeg_lineage_report"]["reaches_patient"]
          and reports["eeg_audit_report"]["verified"])

    # 14. tests pass
    suite = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_eeg_foundation.py"],
        cwd=str(REPO), capture_output=True, text=True)
    check("14. Tests pass", suite.returncode == 0,
          (suite.stdout.strip().splitlines() or [""])[-1])

    # 15. repository boundaries preserved
    bnd = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_boundaries.py"],
                         cwd=str(REPO), capture_output=True, text=True)
    ruff = subprocess.run([sys.executable, "-m", "ruff", "check", "backend/eeg_foundation"],
                          cwd=str(REPO), capture_output=True, text=True)
    check("15. Repository boundaries preserved", bnd.returncode == 0 and ruff.returncode == 0,
          (bnd.stdout.strip().splitlines() or [""])[-1])

    # determinism evidence (printed; folded into the boundary criterion's evidence)
    a = EEGFoundationService(lineage_tracker=LineageTracker()).ingest(fx("valid.edf"))
    b = EEGFoundationService(lineage_tracker=LineageTracker()).ingest(fx("valid.edf"))
    deterministic = a.eeg_id == b.eeg_id and a.metadata.state_signature() == b.metadata.state_signature()

    print("\nPRODUCTIZATION P1 — REAL EEG FOUNDATION — FINAL VALIDATION")
    print("=" * 64)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail and not ok:
            line += f"  -- {detail}"
        print(line)
    print("-" * 64)
    print(f"[{'PASS' if deterministic else 'FAIL'}] determinism: same file -> same id + metadata")
    print("=" * 64)
    print("RESULT:", "ALL CRITERIA PASS" if (all_ok and deterministic) else "FAILURES PRESENT")
    return 0 if (all_ok and deterministic) else 1


def _fam(fmt: str) -> str:
    return {"EDF+": "EDF", "BDF+": "BDF"}.get(fmt, fmt)


if __name__ == "__main__":
    raise SystemExit(main())
