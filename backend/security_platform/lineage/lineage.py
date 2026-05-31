"""Security lineage helpers built on the shared ``ml.lineage`` machinery (DRP5-I).

No parallel lineage system: the security nodes are recorded in the *same*
``ml.lineage.LineageTracker`` as every other node. The chain is

    User -> Credential -> Authentication -> Authorization -> Access Decision -> Resource Access

so a single ``verify_chain`` from a resource-access node reaches the user root. When the
accessed resource exposes a lineage node (a DRP-3 serving execution / DRP-4 persistence
record), the resource-access node also parents it — so the access additionally traces to the
patient.
"""

from __future__ import annotations

from typing import Optional

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    SECURITY_PLATFORM_VERSION, SECURITY_DOMAIN_VERSION, SECURITY_IDENTITY_VERSION,
    SECURITY_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)

__all__ = [
    "make_user_lineage", "make_credential_lineage", "make_authentication_lineage",
    "make_authorization_lineage", "make_access_decision_lineage", "make_resource_access_lineage",
    "security_version_bundle",
]


def security_version_bundle(**extra: object) -> dict:
    bundle = {
        "security_platform_version": SECURITY_PLATFORM_VERSION,
        "security_domain_version": SECURITY_DOMAIN_VERSION,
        "security_identity_version": SECURITY_IDENTITY_VERSION,
        "security_lineage_version": SECURITY_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_user_lineage(user_id: str, *, username: str,
                      created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="security_user", versions=security_version_bundle(), inputs={"username": username},
        outputs={"user_id": user_id}, parents=(), created_at=created_at)


def make_credential_lineage(credential_id: str, user_lineage_id: str, *,
                            created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="credential", versions=security_version_bundle(), inputs={"user_id": user_lineage_id},
        outputs={"credential_id": credential_id}, parents=(user_lineage_id,), created_at=created_at)


def make_authentication_lineage(authentication_id: str, credential_lineage_id: str, *, outcome: str,
                                created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="authentication", versions=security_version_bundle(),
        inputs={"credential_id": credential_lineage_id},
        outputs={"authentication_id": authentication_id, "outcome": outcome},
        parents=(credential_lineage_id,), created_at=created_at)


def make_authorization_lineage(authorization_id: str, authentication_lineage_id: str, *,
                               decision: str,
                               created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="authorization", versions=security_version_bundle(),
        inputs={"authentication_id": authentication_lineage_id},
        outputs={"authorization_id": authorization_id, "decision": decision},
        parents=(authentication_lineage_id,), created_at=created_at)


def make_access_decision_lineage(authorization_lineage_id: str, *, decision: str,
                                 resource_id: str,
                                 created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="access_decision", versions=security_version_bundle(),
        inputs={"authorization_id": authorization_lineage_id},
        outputs={"decision": decision, "resource_id": resource_id},
        parents=(authorization_lineage_id,), created_at=created_at)


def make_resource_access_lineage(access_id: str, decision_lineage_id: str, *, resource_type: str,
                                 resource_id: str, resource_lineage_id: Optional[str] = None,
                                 created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    parents = (decision_lineage_id,)
    if resource_lineage_id:
        parents = (decision_lineage_id, resource_lineage_id)
    return make_lineage_record(
        kind="resource_access", versions=security_version_bundle(),
        inputs={"access_decision": decision_lineage_id, "resource_lineage_id": resource_lineage_id},
        outputs={"access_id": access_id, "resource_type": resource_type, "resource_id": resource_id},
        parents=parents, created_at=created_at)
