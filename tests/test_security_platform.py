"""Tests for DRP-5 — Security Hardening & Access Control Platform.

Exercises authentication, authorization, access control, policy evaluation, registry,
validation, audit, lineage, readiness, reports, schemas, and boundary/invalid/expired/
missing-permission/policy-violation conditions (no replacement systems).
"""

from __future__ import annotations

import dataclasses

import pytest

from ml.lineage import LineageTracker
from backend.security_platform import (
    SecurityPlatformService, SecurityPlatformError, Role, ResourceType, Action, AccessDecision,
    ReadinessClass, AuthOutcome, CredentialManager, AuthenticationEngine, PolicyEngine, AuthorizationEngine, SecurityRegistry, RegistryError, SecurityReadinessEngine, ENTITY_CONTRACTS,
    validate_entity,
)

from _drp5_helpers import build_security_service


# =============================================================================
# Authentication + credential protection (DRP5-C)
# =============================================================================
def test_credentials_never_store_plaintext_and_verify():
    mgr = CredentialManager()
    cred = mgr.register("security_user+" + "a" * 16, "hunter2")
    assert "hunter2" not in cred.to_dict().get("hash_hex", "")
    assert "hunter2" not in str(cred.to_dict())            # no plaintext anywhere
    assert mgr.verify(cred, "hunter2") and not mgr.verify(cred, "wrong")


def test_credential_rotation():
    mgr = CredentialManager()
    cred = mgr.register("security_user+" + "a" * 16, "old-pw")
    rotated_old, new_active = mgr.rotate(cred, "new-pw")
    assert rotated_old.status.value == "rotated" and new_active.status.value == "active"
    assert not mgr.verify(rotated_old, "old-pw")           # rotated credential no longer verifies
    assert mgr.verify(new_active, "new-pw")


def test_authentication_and_session_lifecycle():
    mgr = CredentialManager()
    engine = AuthenticationEngine(credential_manager=mgr)
    cred = mgr.register("security_user+" + "a" * 16, "pw")
    auth, session = engine.authenticate("security_user+" + "a" * 16, cred, "pw", issued_step=0,
                                        ttl_steps=5)
    assert auth.outcome == AuthOutcome.SUCCESS and session is not None
    assert engine.validate_session(session, at_step=3) == (True, "ok")
    assert engine.validate_session(session, at_step=10)[0] is False    # expired by logical TTL
    revoked = engine.revoke_session(session)
    assert engine.validate_session(revoked, at_step=0)[0] is False     # revoked
    # bad password -> failure, no session, never raises
    bad_auth, bad_session = engine.authenticate("security_user+" + "a" * 16, cred, "nope")
    assert bad_auth.outcome == AuthOutcome.FAILURE and bad_session is None


# =============================================================================
# Authorization + policy evaluation (DRP5-D / DRP5-F) — default-deny
# =============================================================================
def test_policy_default_deny_and_explicit_allow():
    pe = PolicyEngine()
    pe.install_default_policies()
    # explicit allow
    d, matched, _ = pe.evaluate(Role.ENGINEER, ResourceType.SERVING, Action.EXECUTE)
    assert d == AccessDecision.PERMITTED and len(matched) >= 1
    # no matching allow -> default deny
    d2, matched2, reason2 = pe.evaluate(Role.RESEARCHER, ResourceType.MODEL, Action.WRITE)
    assert d2 == AccessDecision.DENIED and matched2 == () and "default deny" in reason2
    # explicit deny beats anything
    d3, _, reason3 = pe.evaluate(Role.RESEARCHER, ResourceType.ADMINISTRATIVE, Action.ADMINISTER)
    assert d3 == AccessDecision.DENIED and "deny" in reason3


def test_authorization_is_traceable():
    pe = PolicyEngine()
    pe.install_default_policies()
    authz = AuthorizationEngine().authorize(
        authentication_id="authentication+" + "a" * 16, user_id="security_user+" + "b" * 16,
        role=Role.ADMIN, resource_type=ResourceType.ADMINISTRATIVE, resource_id="admin+1",
        action=Action.ADMINISTER, policy_engine=pe)
    assert authz.decision == AccessDecision.PERMITTED and len(authz.matched_policies) == 1


# =============================================================================
# End-to-end access control (DRP5-E) + registry/audit/lineage integration
# =============================================================================
def test_permitted_access_end_to_end():
    tracker = LineageTracker()
    svc = build_security_service(tracker)
    out = svc.secure_access("erin", "pw-erin-123", resource_type=ResourceType.SERVING,
                            resource_id="serving_execution+" + "a" * 16, action=Action.EXECUTE)
    assert out.accepted and out.permitted and out.reason == AccessDecision.PERMITTED.value
    assert out.readiness.classification == ReadinessClass.READY
    r = out.record
    # registry: orphan-free, access registered
    assert svc.registry.exists(r.access_id) and svc.registry.orphans() == []
    # audit: verified + head match
    log = svc.audit_log_for(r.access_id)
    assert log.verify() and r.audit_head == log.head
    # lineage: the full security chain reaches the user root
    assert tracker.verify_chain(r.lineage_id)
    kinds = {n.kind for n in tracker.chain(r.lineage_id)}
    assert {"security_user", "credential", "authentication", "authorization", "access_decision",
            "resource_access"} <= kinds
    # integrity
    assert svc.integrity(r).ok, [c.name for c in svc.integrity(r).failures()]
    # immutability
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.decision = AccessDecision.DENIED


def test_least_privilege_per_resource_type():
    svc = build_security_service()
    # researcher may read a dataset...
    ok = svc.secure_access("rita", "pw-rita-123", resource_type=ResourceType.DATASET,
                           resource_id="dataset+" + "a" * 16, action=Action.READ)
    assert ok.permitted
    # ...but may NOT write a model (no allow policy -> default deny)
    denied = svc.secure_access("rita", "pw-rita-123", resource_type=ResourceType.MODEL,
                               resource_id="model+" + "a" * 16, action=Action.WRITE)
    assert denied.accepted and not denied.permitted
    # ...and is explicitly denied administrative access (policy violation)
    viol = svc.secure_access("rita", "pw-rita-123", resource_type=ResourceType.ADMINISTRATIVE,
                             resource_id="admin+1", action=Action.ADMINISTER)
    assert not viol.permitted and "deny" in viol.record.reason


def test_admin_can_administer():
    svc = build_security_service()
    out = svc.secure_access("admin", "pw-admin-123", resource_type=ResourceType.ADMINISTRATIVE,
                            resource_id="admin+1", action=Action.ADMINISTER)
    assert out.permitted


# =============================================================================
# Boundary / invalid / expired / missing
# =============================================================================
def test_invalid_credentials_denied_gracefully():
    svc = build_security_service()
    out = svc.secure_access("erin", "WRONG", resource_type=ResourceType.SERVING,
                            resource_id="x", action=Action.EXECUTE)
    assert not out.accepted and out.reason == "authentication_failed"
    assert out.authentication.outcome == AuthOutcome.FAILURE
    assert out.record is None                      # no access record on failed authentication


def test_expired_session_denies_access():
    svc = build_security_service()
    out = svc.secure_access("erin", "pw-erin-123", resource_type=ResourceType.SERVING,
                            resource_id="x", action=Action.EXECUTE, issued_step=0, ttl_steps=5,
                            at_step=99)
    assert out.accepted and not out.permitted and out.record.reason == "session_session_expired" \
        or out.record.reason.startswith("session_")


def test_unknown_user_and_missing_credential_raise():
    svc = SecurityPlatformService(lineage_tracker=LineageTracker())
    with pytest.raises(SecurityPlatformError):
        svc.secure_access("ghost", "pw", resource_type=ResourceType.SERVING, resource_id="x",
                          action=Action.EXECUTE)
    svc.register_user("nopw", Role.ENGINEER)
    with pytest.raises(SecurityPlatformError):
        svc.secure_access("nopw", "pw", resource_type=ResourceType.SERVING, resource_id="x",
                          action=Action.EXECUTE)


# =============================================================================
# Registry orphan guard (DRP5-G)
# =============================================================================
def test_registry_rejects_orphan_access():
    from backend.security_platform.models.domain import SecurityRegistryRecord
    reg = SecurityRegistry()
    rec = SecurityRegistryRecord(
        access_id="access_control+" + "0" * 16, user_id="security_user+" + "0" * 16,
        session_id="security_session+" + "0" * 16, authentication_id="authentication+" + "0" * 16,
        authorization_id="authorization+" + "0" * 16, resource_type="serving", resource_id="x",
        action="execute", decision="permitted", readiness_id="security_readiness+" + "0" * 16,
        version="v", owner="o", creation_date="t", audit_state="", lineage_id="", dependencies=())
    with pytest.raises(RegistryError):
        reg.register_access(rec)


# =============================================================================
# Readiness engine (DRP5-K)
# =============================================================================
def test_readiness_requires_all_evidence():
    eng = SecurityReadinessEngine()
    tid = "access_control+" + "a" * 16
    ready = eng.assess(target_id=tid, authentication_ok=True, authorization_ok=True, policy_ok=True,
                       registered=True, audited=True, traceable=True, validation_ok=True)
    assert ready.classification == ReadinessClass.READY and ready.score == pytest.approx(1.0)
    no_authz = eng.assess(target_id=tid, authentication_ok=True, authorization_ok=False,
                          policy_ok=True, registered=True, audited=True, traceable=True,
                          validation_ok=True)
    assert no_authz.classification != ReadinessClass.READY
    assert "authorization_readiness" in no_authz.findings


# =============================================================================
# Reports (DRP5-L) + schemas (DRP5-M)
# =============================================================================
def test_reports_generate():
    svc = build_security_service()
    out = svc.secure_access("erin", "pw-erin-123", resource_type=ResourceType.SERVING,
                            resource_id="x", action=Action.EXECUTE)
    reports = svc.reports(out.record)
    expected = {"authentication_report", "authorization_report", "access_control_report",
                "policy_report", "validation_report", "readiness_report", "audit_report",
                "lineage_report", "security_summary_report"}
    assert expected == set(reports)
    assert reports["security_summary_report"]["ok"]


def test_entity_contracts_cover_records():
    for name in ("SecurityUserRecord", "CredentialRecord", "SessionRecord", "AuthenticationRecord",
                 "AuthorizationRecord", "SecurityPolicyRecord", "AccessControlRecord",
                 "SecurityReadinessRecord"):
        assert name in ENTITY_CONTRACTS
    ok, missing = validate_entity("CredentialRecord", {
        "credential_id": "c", "user_id": "u", "algorithm": "pbkdf2_hmac_sha256", "iterations": 1,
        "salt_hex": "ab", "hash_hex": "cd", "status": "active"})
    assert ok and missing == []


# =============================================================================
# Cross-run determinism (NR-9/NR-10)
# =============================================================================
def test_cross_run_determinism():
    def run():
        svc = build_security_service()
        return svc.secure_access("erin", "pw-erin-123", resource_type=ResourceType.SERVING,
                                 resource_id="serving_execution+" + "a" * 16,
                                 action=Action.EXECUTE).record
    a, b = run(), run()
    assert a.access_id == b.access_id and a.version.version == b.version.version
    assert a.credential_id == b.credential_id     # deterministic salt -> reproducible credential id
