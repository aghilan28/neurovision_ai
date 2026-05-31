"""Security Platform domain entities + closed vocabularies (DRP5-B).

Pure data shapes (JSON-able, content-hashable). No I/O, no orchestration, no crypto — this
module owns only the *shapes* and the *closed vocabularies* (no free-form states). The
authentication / authorization / access-control / policy engines produce these records; the
service assembles the immutable ``AccessControlRecord`` aggregate.

Mirrors ``backend.persistence_platform.models.domain`` so the security layer is shaped exactly
like the rest of the platform (NR-6).

Secrets discipline (NR-9/NR-10 + secure-by-default): the only non-deterministic inputs are
the salt + the session token. They are quarantined — a ``CredentialRecord`` stores a salted
PBKDF2 hash + salt (verification material, never the plaintext password), and a session stores
only a token *fingerprint*, never the raw token. Every ``signature()`` and content id is a
deterministic function of non-plaintext fields, so ids/versions/audit/lineage reproduce.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    SECURITY_DOMAIN_VERSION, SECURITY_AUTHENTICATION_VERSION, SECURITY_AUTHORIZATION_VERSION,
    SECURITY_CREDENTIAL_VERSION, SECURITY_POLICY_VERSION,
    SECURITY_READINESS_VERSION, SECURITY_REGISTRY_VERSION, SECURITY_VALIDATION_VERSION,
    DETERMINISTIC_EPOCH,
)


# =============================================================================
# Closed vocabularies (no free-form states)
# =============================================================================
class Role(str, Enum):
    """The closed set of roles (RBAC)."""

    ADMIN = "admin"
    ENGINEER = "engineer"
    RESEARCHER = "researcher"
    SERVICE = "service"
    AUDITOR = "auditor"


class Action(str, Enum):
    """The closed set of permissioned actions."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMINISTER = "administer"


class ResourceType(str, Enum):
    """The closed set of protected resource types (DRP5-E)."""

    DATASET = "dataset"
    MODEL = "model"
    SERVING = "serving"
    PERSISTENCE = "persistence"
    ADMINISTRATIVE = "administrative"


class AccessDecision(str, Enum):
    PERMITTED = "permitted"
    DENIED = "denied"


class PolicyEffect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class PolicyStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"


class CredentialStatus(str, Enum):
    ACTIVE = "active"
    ROTATED = "rotated"
    REVOKED = "revoked"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class AuthOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class UserStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class ReadinessClass(str, Enum):
    NOT_READY = "NOT_READY"
    PARTIALLY_READY = "PARTIALLY_READY"
    READY = "READY"


class ReadinessDimension(str, Enum):
    """The closed set of security-readiness dimensions (DRP5-K)."""

    AUTHENTICATION = "authentication_readiness"
    AUTHORIZATION = "authorization_readiness"
    POLICY = "policy_readiness"
    REGISTRY = "registry_readiness"
    AUDIT = "audit_readiness"
    LINEAGE = "lineage_readiness"
    VALIDATION = "validation_readiness"


class EntityKind(str, Enum):
    """The kinds of entity tracked in the security registry."""

    USER = "security_user"
    CREDENTIAL = "credential"
    SESSION = "security_session"
    POLICY = "security_policy"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    ACCESS = "access_control"
    READINESS = "security_readiness"


# =============================================================================
# Identity + versioning projections
# =============================================================================
@dataclass(frozen=True)
class SecurityIdentity:
    """An access-control identity, content-addressed from its authorization + resource."""

    access_id: str
    user_id: str
    session_id: str
    authentication_id: str
    authorization_id: str
    identity_version: str
    domain_version: str = SECURITY_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {
            "access_id": self.access_id, "user_id": self.user_id, "session_id": self.session_id,
            "authentication_id": self.authentication_id, "authorization_id": self.authorization_id,
            "identity_version": self.identity_version, "domain_version": self.domain_version,
        }


@dataclass(frozen=True)
class SecurityVersion:
    version: str
    previous: Optional[str]
    reason: str
    created_at: str = DETERMINISTIC_EPOCH

    @staticmethod
    def compute(state_signature: str, previous: Optional[str]) -> str:
        return hash_obj({"state": state_signature, "previous": previous})

    def to_dict(self) -> dict:
        return {"version": self.version, "previous": self.previous,
                "reason": self.reason, "created_at": self.created_at}


# =============================================================================
# User / credential / session
# =============================================================================
@dataclass(frozen=True)
class SecurityUserRecord:
    user_id: str
    username: str
    role: Role
    status: UserStatus
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    domain_version: str = SECURITY_DOMAIN_VERSION

    def signature(self) -> str:
        return hash_obj({"user_id": self.user_id, "username": self.username, "role": self.role.value,
                         "status": self.status.value})

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id, "username": self.username, "role": self.role.value,
            "status": self.status.value, "created_at": self.created_at, "lineage_id": self.lineage_id,
            "audit_state": self.audit_state, "domain_version": self.domain_version,
            "user_signature": self.signature(),
        }


@dataclass(frozen=True)
class CredentialRecord:
    """A salted PBKDF2 credential. Stores the salt + derived hash (verification material) —
    **never** the plaintext password. The content signature is over non-plaintext fields."""

    credential_id: str
    user_id: str
    algorithm: str
    iterations: int
    salt_hex: str
    hash_hex: str
    status: CredentialStatus
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    credential_version: str = SECURITY_CREDENTIAL_VERSION

    def signature(self) -> str:
        # the hash is a one-way derivative (not plaintext); the salt is verification material
        return hash_obj({"credential_id": self.credential_id, "user_id": self.user_id,
                         "algorithm": self.algorithm, "iterations": self.iterations,
                         "hash_hex": self.hash_hex, "status": self.status.value})

    def to_dict(self) -> dict:
        return {
            "credential_id": self.credential_id, "user_id": self.user_id, "algorithm": self.algorithm,
            "iterations": self.iterations, "salt_hex": self.salt_hex, "hash_hex": self.hash_hex,
            "status": self.status.value, "created_at": self.created_at, "lineage_id": self.lineage_id,
            "credential_version": self.credential_version, "credential_signature": self.signature(),
        }


@dataclass(frozen=True)
class SessionRecord:
    """A session: stores only a token *fingerprint* (never the raw token). Expiry is a
    deterministic logical-step window (no wall-clock)."""

    session_id: str
    user_id: str
    credential_id: str
    token_fingerprint: str
    status: SessionStatus
    issued_step: int
    ttl_steps: int
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    domain_version: str = SECURITY_DOMAIN_VERSION

    def expires_step(self) -> int:
        return self.issued_step + self.ttl_steps

    def signature(self) -> str:
        return hash_obj({"session_id": self.session_id, "user_id": self.user_id,
                         "credential_id": self.credential_id,
                         "token_fingerprint": self.token_fingerprint, "status": self.status.value,
                         "issued_step": self.issued_step, "ttl_steps": self.ttl_steps})

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id, "user_id": self.user_id, "credential_id": self.credential_id,
            "token_fingerprint": self.token_fingerprint, "status": self.status.value,
            "issued_step": self.issued_step, "ttl_steps": self.ttl_steps,
            "expires_step": self.expires_step(), "created_at": self.created_at,
            "lineage_id": self.lineage_id, "domain_version": self.domain_version,
            "session_signature": self.signature(),
        }


# =============================================================================
# Authentication / authorization / access
# =============================================================================
@dataclass(frozen=True)
class AuthenticationRecord:
    authentication_id: str
    user_id: str
    credential_id: str
    session_id: Optional[str]
    outcome: AuthOutcome
    reason: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    authentication_version: str = SECURITY_AUTHENTICATION_VERSION

    def signature(self) -> str:
        return hash_obj({"authentication_id": self.authentication_id, "user_id": self.user_id,
                         "credential_id": self.credential_id, "session_id": self.session_id,
                         "outcome": self.outcome.value, "reason": self.reason})

    def to_dict(self) -> dict:
        return {
            "authentication_id": self.authentication_id, "user_id": self.user_id,
            "credential_id": self.credential_id, "session_id": self.session_id,
            "outcome": self.outcome.value, "reason": self.reason, "created_at": self.created_at,
            "lineage_id": self.lineage_id, "authentication_version": self.authentication_version,
            "authentication_signature": self.signature(),
        }


@dataclass(frozen=True)
class AuthorizationRecord:
    authorization_id: str
    user_id: str
    role: Role
    resource_type: ResourceType
    resource_id: str
    action: Action
    decision: AccessDecision
    matched_policies: tuple[str, ...]
    reason: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    authorization_version: str = SECURITY_AUTHORIZATION_VERSION

    def signature(self) -> str:
        return hash_obj({
            "authorization_id": self.authorization_id, "user_id": self.user_id, "role": self.role.value,
            "resource_type": self.resource_type.value, "resource_id": self.resource_id,
            "action": self.action.value, "decision": self.decision.value,
            "matched_policies": list(self.matched_policies), "reason": self.reason,
        })

    def to_dict(self) -> dict:
        return {
            "authorization_id": self.authorization_id, "user_id": self.user_id, "role": self.role.value,
            "resource_type": self.resource_type.value, "resource_id": self.resource_id,
            "action": self.action.value, "decision": self.decision.value,
            "matched_policies": list(self.matched_policies), "reason": self.reason,
            "created_at": self.created_at, "lineage_id": self.lineage_id,
            "authorization_version": self.authorization_version,
            "authorization_signature": self.signature(),
        }


@dataclass(frozen=True)
class SecurityPolicyRecord:
    policy_id: str
    name: str
    role: Role
    resource_type: ResourceType
    action: Action
    effect: PolicyEffect
    status: PolicyStatus
    version: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    policy_version: str = SECURITY_POLICY_VERSION

    def signature(self) -> str:
        return hash_obj({"policy_id": self.policy_id, "name": self.name, "role": self.role.value,
                         "resource_type": self.resource_type.value, "action": self.action.value,
                         "effect": self.effect.value, "status": self.status.value,
                         "version": self.version})

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id, "name": self.name, "role": self.role.value,
            "resource_type": self.resource_type.value, "action": self.action.value,
            "effect": self.effect.value, "status": self.status.value, "version": self.version,
            "created_at": self.created_at, "lineage_id": self.lineage_id,
            "policy_version_tag": self.policy_version, "policy_signature": self.signature(),
        }


# =============================================================================
# Validation / readiness projections
# =============================================================================
@dataclass(frozen=True)
class SecurityValidationRecord:
    validation_id: str
    ok: bool
    checks: tuple[tuple, ...]            # (name, passed, detail)
    validation_version: str = SECURITY_VALIDATION_VERSION

    @property
    def n_checks(self) -> int:
        return len(self.checks)

    def signature(self) -> str:
        return hash_obj({"ok": self.ok, "checks": [[n, bool(p)] for n, p, _ in self.checks]})

    def to_dict(self) -> dict:
        return {
            "validation_id": self.validation_id, "ok": self.ok, "n_checks": self.n_checks,
            "checks": [{"name": n, "passed": bool(p), "detail": d} for n, p, d in self.checks],
            "validation_version": self.validation_version, "validation_signature": self.signature(),
        }


@dataclass(frozen=True)
class SecurityReadinessRecord:
    readiness_id: str
    target_id: str
    score: float
    classification: ReadinessClass
    dimensions: dict
    findings: tuple[str, ...]
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    readiness_version: str = SECURITY_READINESS_VERSION

    def signature(self) -> str:
        return hash_obj({
            "readiness_id": self.readiness_id, "target_id": self.target_id,
            "score": round(float(self.score), 9), "classification": self.classification.value,
            "dimensions": {k: round(float(v), 9) for k, v in sorted(self.dimensions.items())},
            "findings": list(self.findings),
        })

    def to_dict(self) -> dict:
        return {
            "readiness_id": self.readiness_id, "target_id": self.target_id,
            "score": round(float(self.score), 9), "classification": self.classification.value,
            "dimensions": {k: round(float(v), 9) for k, v in sorted(self.dimensions.items())},
            "findings": list(self.findings), "created_at": self.created_at,
            "lineage_id": self.lineage_id, "readiness_version": self.readiness_version,
            "readiness_signature": self.signature(),
        }


# =============================================================================
# Audit / lineage projections
# =============================================================================
@dataclass(frozen=True)
class SecurityAuditRecord:
    """An immutable audit event in the hash-chained security audit log (the shared
    ``ImmutableAuditLog`` implementation; no parallel system)."""

    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {
            "seq": self.seq, "kind": self.kind, "payload": self.payload,
            "prev_hash": self.prev_hash, "event_hash": self.event_hash, "created_at": self.created_at,
        }


@dataclass(frozen=True)
class SecurityLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


# =============================================================================
# Registry record
# =============================================================================
@dataclass
class SecurityRegistryRecord:
    """The security registry entry shape for one end-to-end access (mutated only via governed
    registry methods)."""

    access_id: str
    user_id: str
    session_id: str
    authentication_id: str
    authorization_id: str
    resource_type: str
    resource_id: str
    action: str
    decision: str
    readiness_id: str
    version: str
    owner: str
    creation_date: str
    audit_state: str
    lineage_id: str
    dependencies: tuple[str, ...]
    registry_version: str = SECURITY_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({
            "access_id": self.access_id, "user_id": self.user_id, "session_id": self.session_id,
            "authentication_id": self.authentication_id, "authorization_id": self.authorization_id,
            "resource_type": self.resource_type, "resource_id": self.resource_id,
            "action": self.action, "decision": self.decision, "version": self.version,
            "lineage_id": self.lineage_id,
        })

    def to_dict(self) -> dict:
        return {
            "access_id": self.access_id, "user_id": self.user_id, "session_id": self.session_id,
            "authentication_id": self.authentication_id, "authorization_id": self.authorization_id,
            "resource_type": self.resource_type, "resource_id": self.resource_id,
            "action": self.action, "decision": self.decision, "readiness_id": self.readiness_id,
            "version": self.version, "owner": self.owner, "creation_date": self.creation_date,
            "audit_state": self.audit_state, "lineage_id": self.lineage_id,
            "dependencies": list(self.dependencies), "registry_version": self.registry_version,
            "content_signature": self.content_signature(),
        }


# =============================================================================
# The aggregate — the immutable Access Control record
# =============================================================================
@dataclass(frozen=True)
class AccessControlRecord:
    """The security aggregate — an **immutable**, versioned, auditable, lineage-tracked record
    of one end-to-end access decision. Binds the user, the credential, the authentication +
    session, the authorization, the access decision, and the resource accessed."""

    identity: SecurityIdentity
    user_id: str
    role: Role
    credential_id: str
    session_id: str
    authentication_id: str
    authorization_id: str
    resource_type: ResourceType
    resource_id: str
    action: Action
    decision: AccessDecision
    matched_policies: tuple[str, ...]
    reason: str
    validation: SecurityValidationRecord
    readiness_id: str
    readiness_class: ReadinessClass
    version: SecurityVersion
    owner: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    dependencies: tuple[str, ...] = ()
    domain_version: str = SECURITY_DOMAIN_VERSION

    @property
    def access_id(self) -> str:
        return self.identity.access_id

    @property
    def permitted(self) -> bool:
        return self.decision == AccessDecision.PERMITTED

    @staticmethod
    def state_signature_of(*, identity, user_id, role, credential_id, session_id,
                           authentication_id, authorization_id, resource_type, resource_id, action,
                           decision, matched_policies, reason, validation, readiness_id,
                           readiness_class, dependencies) -> str:
        return hash_obj({
            "access_id": identity.access_id, "user_id": user_id, "role": role.value,
            "credential_id": credential_id, "session_id": session_id,
            "authentication_id": authentication_id, "authorization_id": authorization_id,
            "resource_type": resource_type.value, "resource_id": resource_id, "action": action.value,
            "decision": decision.value, "matched_policies": list(matched_policies), "reason": reason,
            "validation_signature": validation.signature(), "readiness_id": readiness_id,
            "readiness_class": readiness_class.value, "dependencies": list(dependencies),
        })

    def state_signature(self) -> str:
        return self.state_signature_of(
            identity=self.identity, user_id=self.user_id, role=self.role,
            credential_id=self.credential_id, session_id=self.session_id,
            authentication_id=self.authentication_id, authorization_id=self.authorization_id,
            resource_type=self.resource_type, resource_id=self.resource_id, action=self.action,
            decision=self.decision, matched_policies=self.matched_policies, reason=self.reason,
            validation=self.validation, readiness_id=self.readiness_id,
            readiness_class=self.readiness_class, dependencies=self.dependencies)

    def to_dict(self) -> dict:
        return {
            "domain_version": self.domain_version, "identity": self.identity.to_dict(),
            "user_id": self.user_id, "role": self.role.value, "credential_id": self.credential_id,
            "session_id": self.session_id, "authentication_id": self.authentication_id,
            "authorization_id": self.authorization_id, "resource_type": self.resource_type.value,
            "resource_id": self.resource_id, "action": self.action.value,
            "decision": self.decision.value, "matched_policies": list(self.matched_policies),
            "reason": self.reason, "validation": self.validation.to_dict(),
            "readiness_id": self.readiness_id, "readiness_class": self.readiness_class.value,
            "version": self.version.to_dict(), "owner": self.owner, "created_at": self.created_at,
            "lineage_id": self.lineage_id, "audit_head": self.audit_head,
            "dependencies": list(self.dependencies), "state_signature": self.state_signature(),
        }
