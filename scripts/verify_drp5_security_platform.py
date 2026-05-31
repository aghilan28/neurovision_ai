"""Final validation for DRP-5 — Security Hardening & Access Control Platform.

Verifies the directive's 15 criteria against the real subsystem, exercising authentication,
authorization, access control, policy evaluation, and access over a **real** DRP-3 serving
resource on one shared lineage tracker (no replacement systems).

    python -m scripts.verify_drp5_security_platform
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    checks: list[tuple] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "tests"))
    from ml.lineage import LineageTracker
    from backend.security_platform import (
        SecurityPlatformService, Role, ResourceType, Action, AccessDecision, ReadinessClass,
        AuthOutcome,
    )
    from _eeg_fixtures import generate_fixtures
    from _drp5_helpers import build_real_serving_resource

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="drp5_verify_"))
    eeg = generate_fixtures(str(tmp / "fix"))
    tracker = LineageTracker()
    execution_id, exec_lineage_id = build_real_serving_resource(eeg, tmp, tracker)

    svc = SecurityPlatformService(lineage_tracker=tracker)
    svc.register_user("erin", Role.ENGINEER)
    svc.register_user("rita", Role.RESEARCHER)
    svc.register_user("admin", Role.ADMIN)
    for n in ("erin", "rita", "admin"):
        svc.set_credential(n, f"pw-{n}-123")

    permit = svc.secure_access("erin", "pw-erin-123", resource_type=ResourceType.SERVING,
                               resource_id=execution_id, action=Action.EXECUTE,
                               resource_lineage_id=exec_lineage_id)
    deny = svc.secure_access("rita", "pw-rita-123", resource_type=ResourceType.ADMINISTRATIVE,
                             resource_id="admin+1", action=Action.ADMINISTER)
    bad = svc.secure_access("erin", "WRONG", resource_type=ResourceType.SERVING,
                            resource_id=execution_id, action=Action.EXECUTE)
    record = permit.record

    # --- 1. authentication works ---
    try:
        ok = (permit.authentication.outcome == AuthOutcome.SUCCESS
              and bad.authentication.outcome == AuthOutcome.FAILURE and not bad.accepted)
        check("1. Authentication works", ok, "success + graceful failure on bad credentials")
    except Exception as exc:
        check("1. Authentication works", False, f"error: {exc}")

    # --- 2. authorization works ---
    try:
        ok = permit.permitted and not deny.permitted
        check("2. Authorization works", ok, "permit (explicit allow) + deny")
    except Exception as exc:
        check("2. Authorization works", False, f"error: {exc}")

    # --- 3. access control works ---
    try:
        ok = (permit.record.decision == AccessDecision.PERMITTED
              and deny.record.decision == AccessDecision.DENIED)
        check("3. Access control works", ok, "least-privilege grant + default-deny")
    except Exception as exc:
        check("3. Access control works", False, f"error: {exc}")

    # --- 4. policy evaluation works ---
    try:
        pol_ok, problems = svc.policies.validate()
        ok = pol_ok and len(svc.policies.list_policies()) >= 10 and "deny" in deny.record.reason
        check("4. Policy evaluation works", ok,
              f"n_policies={len(svc.policies.list_policies())} problems={problems}")
    except Exception as exc:
        check("4. Policy evaluation works", False, f"error: {exc}")

    # --- 5. validation works ---
    try:
        report = svc.integrity(record)
        check("5. Validation works", report.ok,
              "all integrity checks pass" if report.ok else
              f"failed={[c.name for c in report.failures()]}")
    except Exception as exc:
        check("5. Validation works", False, f"error: {exc}")

    # --- 6. registry works ---
    try:
        counts = svc.registry.counts()
        ok = (svc.registry.exists(record.access_id) and svc.registry.orphans() == []
              and counts["access_control"] >= 2 and counts["security_policy"] >= 10)
        check("6. Registry works", ok, f"counts={counts} orphans={len(svc.registry.orphans())}")
    except Exception as exc:
        check("6. Registry works", False, f"error: {exc}")

    # --- 7. audit integration works ---
    try:
        log = svc.audit_log_for(record.access_id)
        ok = log.verify() and record.audit_head == log.head and len(log) >= 6
        check("7. Audit integration works", ok, f"events={len(log)} verified={log.verify()}")
    except Exception as exc:
        check("7. Audit integration works", False, f"error: {exc}")

    # --- 8. lineage integration works ---
    try:
        kinds = {n.kind for n in tracker.chain(record.lineage_id)}
        required = {"security_user", "credential", "authentication", "authorization",
                    "access_decision", "resource_access"}
        ok = (required <= kinds and tracker.verify_chain(record.lineage_id)
              and {"patient", "serving_execution"} <= kinds)   # reaches the real resource + patient
        check("8. Lineage integration works", ok, f"kinds>={sorted(required)} +patient")
    except Exception as exc:
        check("8. Lineage integration works", False, f"error: {exc}")

    # --- 9. readiness works ---
    try:
        ok = permit.readiness.classification == ReadinessClass.READY \
            and len(permit.readiness.dimensions) == 7
        check("9. Readiness works", ok, f"classification={permit.readiness.classification.value}")
    except Exception as exc:
        check("9. Readiness works", False, f"error: {exc}")

    # --- 10. reports generate ---
    try:
        reports = svc.reports(record)
        expected = {"authentication_report", "authorization_report", "access_control_report",
                    "policy_report", "validation_report", "readiness_report", "audit_report",
                    "lineage_report", "security_summary_report"}
        check("10. Reports generate", expected == set(reports), f"reports={len(reports)}")
    except Exception as exc:
        check("10. Reports generate", False, f"error: {exc}")

    # --- 13. determinism preserved (security ids over a FIXED resource id, so this isolates
    #     the security platform's determinism from the upstream serving pipeline) ---
    try:
        fixed_resource = "serving_execution+" + "a" * 16

        def _run_security():
            t = LineageTracker()
            s = SecurityPlatformService(lineage_tracker=t)
            s.register_user("erin", Role.ENGINEER)
            s.set_credential("erin", "pw-erin-123")
            return s.secure_access("erin", "pw-erin-123", resource_type=ResourceType.SERVING,
                                   resource_id=fixed_resource, action=Action.EXECUTE).record
        a, b = _run_security(), _run_security()
        ok = (a.access_id == b.access_id and a.version.version == b.version.version
              and a.credential_id == b.credential_id)
        check("13. Determinism preserved", ok, "same access id + version + credential id")
    except Exception as exc:
        check("13. Determinism preserved", False, f"error: {exc}")

    # --- 14. security traceability preserved ---
    try:
        ok = tracker.verify_chain(record.lineage_id) and svc.integrity(record).ok
        check("14. Security traceability preserved", ok,
              "User -> Credential -> Authentication -> Authorization -> Access Decision -> Resource Access")
    except Exception as exc:
        check("14. Security traceability preserved", False, f"error: {exc}")

    # --- 15. security platform completed ---
    try:
        ok = (permit.permitted and not deny.permitted and not bad.accepted
              and permit.readiness.classification == ReadinessClass.READY and svc.integrity(record).ok)
        check("15. Security platform completed", ok,
              "authenticate -> authorize -> control -> audit -> trace -> score, all green")
    except Exception as exc:
        check("15. Security platform completed", False, f"error: {exc}")

    # --- 11. tests pass ---
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               "tests/test_security_platform.py",
                               "tests/test_security_platform_e2e.py"], cwd=str(REPO),
                              capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("11. Tests pass", proc.returncode == 0, tail)
    except Exception as exc:
        check("11. Tests pass", False, f"error: {exc}")

    # --- 12. repository boundaries preserved ---
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               "tests/test_boundaries.py"], cwd=str(REPO),
                              capture_output=True, text=True)
        tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        check("12. Repository boundaries preserved", proc.returncode == 0, tail)
    except Exception as exc:
        check("12. Repository boundaries preserved", False, f"error: {exc}")

    order = {f"{i}.": i for i in range(1, 16)}
    checks.sort(key=lambda c: order.get(c[0].split(" ")[0], 99))
    print("\nDRP-5 — SECURITY PLATFORM — FINAL VALIDATION")
    print("=" * 64)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"   -- {detail}"
        print(line)
    print("-" * 64)
    print("SECURITY:", f"permit={permit.permitted} deny={not deny.permitted} "
          f"bad_creds_rejected={not bad.accepted} readiness={permit.readiness.classification.value}")
    print("-" * 64)
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
