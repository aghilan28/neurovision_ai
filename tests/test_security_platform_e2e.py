"""End-to-end test for DRP-5 — Security Hardening & Access Control Platform.

Demonstrates the full required deliverable: authenticate -> authorize -> evaluate policies ->
control access -> audit -> trace lineage -> score readiness — controlling access to a **real**
DRP-3 serving resource on one shared lineage tracker (no replacement systems), so the access
additionally traces to the patient.
"""

from __future__ import annotations

from ml.lineage import LineageTracker
from backend.security_platform import (
    SecurityPlatformService, Role, ResourceType, Action, ReadinessClass,
)

from _drp5_helpers import build_real_serving_resource


def test_full_security_deliverable_over_real_serving_resource(eeg_fixtures, tmp_path):
    tracker = LineageTracker()
    # a real DRP-3 served execution on the shared tracker
    execution_id, exec_lineage_id = build_real_serving_resource(eeg_fixtures, tmp_path, tracker)

    svc = SecurityPlatformService(lineage_tracker=tracker)
    svc.register_user("erin", Role.ENGINEER)
    svc.set_credential("erin", "pw-erin-123")

    out = svc.secure_access("erin", "pw-erin-123", resource_type=ResourceType.SERVING,
                            resource_id=execution_id, action=Action.EXECUTE,
                            resource_lineage_id=exec_lineage_id)
    assert out.accepted and out.permitted
    assert out.readiness.classification == ReadinessClass.READY
    assert svc.integrity(out.record).ok

    # the access chain reaches the user root AND (via the real serving resource) the patient
    assert tracker.verify_chain(out.record.lineage_id)
    kinds = {n.kind for n in tracker.chain(out.record.lineage_id)}
    assert {"security_user", "credential", "authentication", "authorization", "access_decision",
            "resource_access"} <= kinds
    assert {"patient", "model", "prediction", "serving_execution"} <= kinds   # reaches the patient

    # all nine reports
    assert len(svc.reports(out.record)) == 9


def test_persistence_resource_access_least_privilege(eeg_fixtures, tmp_path):
    """An auditor may READ persistence; a service account may not (default deny)."""
    svc = SecurityPlatformService(lineage_tracker=LineageTracker())
    svc.register_user("aud", Role.AUDITOR)
    svc.register_user("svc", Role.SERVICE)
    svc.set_credential("aud", "pw-aud-123")
    svc.set_credential("svc", "pw-svc-123")

    allowed = svc.secure_access("aud", "pw-aud-123", resource_type=ResourceType.PERSISTENCE,
                                resource_id="persistence_record+" + "a" * 16, action=Action.READ)
    assert allowed.permitted
    denied = svc.secure_access("svc", "pw-svc-123", resource_type=ResourceType.PERSISTENCE,
                               resource_id="persistence_record+" + "a" * 16, action=Action.READ)
    assert denied.accepted and not denied.permitted    # default deny for the service role


def test_audit_is_immutable_and_traceable(eeg_fixtures, tmp_path):
    svc = SecurityPlatformService(lineage_tracker=LineageTracker())
    svc.register_user("erin", Role.ENGINEER)
    svc.set_credential("erin", "pw-erin-123")
    out = svc.secure_access("erin", "pw-erin-123", resource_type=ResourceType.SERVING,
                            resource_id="serving_execution+" + "a" * 16, action=Action.EXECUTE)
    log = svc.audit_log_for(out.record.access_id)
    kinds = [e.kind for e in log.events()]
    assert "authentication" in kinds and "authorization" in kinds and "resource_access" in kinds
    assert log.verify()
