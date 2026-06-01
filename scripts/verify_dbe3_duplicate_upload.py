"""Final validation for DBE-3 — Duplicate Upload Reliability Fix.

Verifies the directive's 15 criteria against the **real** upload workflow + the real FastAPI
app, using a real EEG fixture. It (1) reproduces the original failure mode at the registry
level (the documented root cause), (2) proves the live upload endpoint now classifies + handles
duplicates deterministically and never returns 500, and (3) asserts registry/audit/lineage/
readiness integrity after repeated duplicates.

    python -m scripts.verify_dbe3_duplicate_upload
"""

from __future__ import annotations

import _repo_bootstrap  # noqa: F401

import base64
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

    from backend.application_platform import create_app
    from backend.application_platform.models.domain import ApplicationRegistryRecord, EntityKind
    from backend.application_platform.registry import ApplicationRegistry, RegistryError
    from backend.application_platform.uploads.duplicates import DuplicateDetector, content_hash
    from _track3_helpers import make_product, real_eeg_bytes

    # --- 1. Bug reproduced (the original failure mode, at the registry level) ---
    # The audit's root cause: re-registering the SAME entity id with a registry signature that
    # embeds the advanced audit head -> RegistryError -> (unhandled) HTTP 500. Reproduce it:
    try:
        reg = ApplicationRegistry()
        rec1 = ApplicationRegistryRecord(
            entity_kind=EntityKind.UPLOAD, entity_id="app_upload+demo", status="active",
            version="v", owner="o", creation_date="t", audit_state="head1", lineage_id="ln")
        reg.register(rec1)
        reproduced = False
        try:
            rec2 = ApplicationRegistryRecord(
                entity_kind=EntityKind.UPLOAD, entity_id="app_upload+demo", status="active",
                version="v", owner="o", creation_date="t", audit_state="head2",  # advanced head
                lineage_id="ln")
            reg.register(rec2)
        except RegistryError:
            reproduced = True
        check("1. Bug reproduced", reproduced,
              "re-register same id with advanced audit head -> RegistryError (the 500 root cause)")
    except Exception as exc:
        check("1. Bug reproduced", False, f"error: {exc}")

    # --- 2. Root cause identified (documented) ---
    doc = REPO / "backend" / "application_platform" / "docs" / "DUPLICATE_UPLOADS.md"
    doc_txt = doc.read_text() if doc.exists() else ""
    check("2. Root cause identified", "audit head" in doc_txt and "content_signature" in doc_txt,
          "root cause documented in DUPLICATE_UPLOADS.md")

    # --- build the real product + drive the live API ---
    svc = make_product(analysis_seconds=2.0)
    client = TestClient(create_app(svc), raise_server_exceptions=False)
    client.post("/v1/auth/register", json={"username": "u", "password": "pw-123456"})
    tok = client.post("/v1/auth/login",
                      json={"username": "u", "password": "pw-123456"}).json()["token"]
    content = real_eeg_bytes()

    def up(c=content, filename="v.edf"):
        return client.post("/v1/uploads",
                           json={"filename": filename, "content_base64": base64.b64encode(c).decode()},
                           headers={"Authorization": f"Bearer {tok}"})

    r1 = up()
    r2 = up()
    r3 = up()
    r_rename = up(filename="renamed.edf")
    statuses = [r1.status_code, r2.status_code, r3.status_code, r_rename.status_code]

    # --- 3. Duplicate detection works ---
    det = DuplicateDetector()
    d0 = det.classify(content=content, upload_id="app_upload+x", valid=True)
    det.record(content_hash_value=d0.content_hash, upload_id="app_upload+x", analysis_id="a")
    d1 = det.classify(content=content, upload_id="app_upload+x", valid=True)
    check("3. Duplicate detection works",
          d0.classification.value == "NEW_UPLOAD" and d1.classification.value == "EXACT_DUPLICATE",
          f"new={d0.classification.value} dup={d1.classification.value}")

    # --- 4. Classification works (closed vocabulary on the live API) ---
    cls2 = r2.json().get("duplicate_classification")
    check("4. Classification works", cls2 in ("EXACT_DUPLICATE", "CONTENT_DUPLICATE")
          and r1.json().get("duplicate_classification") == "NEW_UPLOAD",
          f"first={r1.json().get('duplicate_classification')} dup={cls2}")

    # --- 5. Duplicate uploads do not crash ---
    check("5. Duplicate uploads do not crash", all(s in (200, 201) for s in statuses),
          f"statuses={statuses}")

    # --- 6. No 500 responses ---
    check("6. No 500 responses", 500 not in statuses and r2.status_code == 200,
          f"statuses={statuses} (dup -> 200)")

    # --- 7. Registry integrity preserved ---
    counts = svc.registry.counts()
    check("7. Registry integrity preserved",
          svc.registry.orphans() == [] and counts["app_upload"] == 1 and counts["app_analysis"] == 1,
          f"counts(app_upload={counts['app_upload']}, app_analysis={counts['app_analysis']}) orphans=0")

    # --- 8. Audit integrity preserved ---
    check("8. Audit integrity preserved", svc.audit.verify()
          and "upload_duplicate" in [e.kind for e in svc.audit.events()],
          f"verified={svc.audit.verify()} duplicate-events recorded")

    # --- 9. Lineage integrity preserved ---
    aid = r1.json()["analysis_id"]
    outcome = svc.get_analysis(aid)
    check("9. Lineage integrity preserved", svc.lineage.verify_chain(outcome.report_record.lineage_id),
          "report chain verifies after duplicates")

    # --- 10. Readiness preserved ---
    check("10. Readiness preserved",
          r1.json()["readiness"]["classification"] == "READY_FOR_USERS"
          and r2.json()["readiness"]["classification"] == "READY_FOR_USERS",
          "READY_FOR_USERS on new + duplicate")

    # --- 13. determinism preserved ---
    a = content_hash(content)
    b = content_hash(content)
    svc2 = make_product(analysis_seconds=2.0)
    c2 = TestClient(create_app(svc2), raise_server_exceptions=False)
    c2.post("/v1/auth/register", json={"username": "u", "password": "pw-123456"})
    t2 = c2.post("/v1/auth/login", json={"username": "u", "password": "pw-123456"}).json()["token"]
    r1b = c2.post("/v1/uploads",
                  json={"filename": "v.edf", "content_base64": base64.b64encode(content).decode()},
                  headers={"Authorization": f"Bearer {t2}"})
    check("13. Determinism preserved",
          a == b and r1b.json()["analysis_id"] == r1.json()["analysis_id"],
          "same content hash + same analysis id across instances")

    # --- 14. behavior documented ---
    documented = all(k in doc_txt for k in ("NEW_UPLOAD", "EXACT_DUPLICATE", "CONTENT_DUPLICATE",
                                            "CONFLICTING_UPLOAD", "INVALID_UPLOAD", "409", "200"))
    check("14. Behavior documented", documented, f"{doc.name} documents all classes + status codes")

    # --- 11. tests pass ---
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_duplicate_upload.py"], cwd=str(REPO),
                           capture_output=True, text=True)
        check("11. Tests pass", p.returncode == 0,
              p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "")
    except Exception as exc:
        check("11. Tests pass", False, f"error: {exc}")

    # --- 12. repository boundaries preserved ---
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_boundaries.py"], cwd=str(REPO),
                           capture_output=True, text=True)
        check("12. Repository boundaries preserved", p.returncode == 0,
              p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "")
    except Exception as exc:
        check("12. Repository boundaries preserved", False, f"error: {exc}")

    # --- 15. DBE-3 completed ---
    completed = all(ok for n, ok, _ in checks if not n.startswith("15."))
    check("15. DBE-3 completed", completed,
          "duplicate uploads classified + handled deterministically; no 500; integrity preserved")

    order = {f"{i}.": i for i in range(1, 16)}
    checks.sort(key=lambda c: order.get(c[0].split(" ")[0], 99))
    print("\nDBE-3 — DUPLICATE UPLOAD RELIABILITY — FINAL VALIDATION")
    print("=" * 64)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 64)
    print(f"UPLOAD STATUSES (new, dup, dup, renamed): {statuses}  (no 500 anywhere)")
    print("-" * 64)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
