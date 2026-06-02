"""The security registry (DRP5-G).

Tracks users, credentials, sessions, policies, access decisions (the end-to-end
``AccessControlRecord`` registry entries), and validation results, with audit + lineage
references. **No orphan records**: every access entry references a lineage node + an audit
head + a registered user/credential/session, and re-registering the same ``(access_id,
version)`` with different content is rejected (silent overwrite forbidden).
"""

from __future__ import annotations

from ..models.domain import (
    AuthenticationRecord, AuthorizationRecord, CredentialRecord, EntityKind, SecurityReadinessRecord, SecurityRegistryRecord, SecurityUserRecord, SessionRecord,
)
from ..version import SECURITY_REGISTRY_VERSION

GENESIS = "0" * 16


class RegistryError(RuntimeError):
    """Raised on an orphan registration or a silent-overwrite attempt."""


class SecurityRegistry:
    """In-memory registry of security artifacts, keyed by id."""

    version = SECURITY_REGISTRY_VERSION

    def __init__(self) -> None:
        self._users: dict[str, SecurityUserRecord] = {}
        self._credentials: dict[str, CredentialRecord] = {}
        self._sessions: dict[str, SessionRecord] = {}
        self._authentications: dict[str, AuthenticationRecord] = {}
        self._authorizations: dict[str, AuthorizationRecord] = {}
        self._accesses: dict[str, SecurityRegistryRecord] = {}
        self._readiness: dict[str, SecurityReadinessRecord] = {}
        self._policy_engine = None
        self._version_sigs: dict[tuple[str, str], str] = {}

    # --- registration ---------------------------------------------------------
    def register_user(self, rec: SecurityUserRecord) -> SecurityUserRecord:
        self._users[rec.user_id] = rec
        return rec

    def register_credential(self, rec: CredentialRecord) -> CredentialRecord:
        self._credentials[rec.credential_id] = rec
        return rec

    def register_session(self, rec: SessionRecord) -> SessionRecord:
        self._sessions[rec.session_id] = rec
        return rec

    def register_authentication(self, rec: AuthenticationRecord) -> AuthenticationRecord:
        self._authentications[rec.authentication_id] = rec
        return rec

    def register_authorization(self, rec: AuthorizationRecord) -> AuthorizationRecord:
        self._authorizations[rec.authorization_id] = rec
        return rec

    def register_readiness(self, rec: SecurityReadinessRecord) -> SecurityReadinessRecord:
        self._readiness[rec.readiness_id] = rec
        return rec

    def attach_policy_engine(self, policy_engine) -> None:
        self._policy_engine = policy_engine

    def register_access(self, rec: SecurityRegistryRecord) -> SecurityRegistryRecord:
        if not rec.lineage_id:
            raise RegistryError(f"{rec.access_id!r} has no lineage node (orphans forbidden)")
        if not rec.audit_state or rec.audit_state == GENESIS:
            raise RegistryError(f"{rec.access_id!r} has no audit head (orphans forbidden)")
        if rec.user_id not in self._users or rec.session_id not in self._sessions \
                or rec.authentication_id not in self._authentications \
                or rec.authorization_id not in self._authorizations \
                or rec.readiness_id not in self._readiness:
            raise RegistryError(f"{rec.access_id!r} references unregistered prerequisites (orphans)")
        key = (rec.access_id, rec.version)
        sig = rec.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise RegistryError(
                f"access {rec.access_id} v{rec.version} already registered with different content")
        self._version_sigs[key] = sig
        self._accesses[rec.access_id] = rec
        return rec

    # --- accessors ------------------------------------------------------------
    def get_access(self, access_id: str) -> SecurityRegistryRecord:
        if access_id not in self._accesses:
            raise KeyError(f"access {access_id!r} not in registry")
        return self._accesses[access_id]

    def exists(self, access_id: str) -> bool:
        return access_id in self._accesses

    def list_accesses(self) -> list[str]:
        return sorted(self._accesses)

    def by_decision(self, decision: str) -> list[str]:
        return sorted(a for a, r in self._accesses.items() if r.decision == decision)

    def counts(self) -> dict:
        n_policies = len(self._policy_engine.list_policies()) if self._policy_engine else 0
        return {
            EntityKind.USER.value: len(self._users),
            EntityKind.CREDENTIAL.value: len(self._credentials),
            EntityKind.SESSION.value: len(self._sessions),
            EntityKind.POLICY.value: n_policies,
            EntityKind.AUTHENTICATION.value: len(self._authentications),
            EntityKind.AUTHORIZATION.value: len(self._authorizations),
            EntityKind.ACCESS.value: len(self._accesses),
            EntityKind.READINESS.value: len(self._readiness),
        }

    def orphans(self) -> list[str]:
        out = []
        for aid, r in self._accesses.items():
            if (r.user_id not in self._users or r.session_id not in self._sessions
                    or r.authentication_id not in self._authentications
                    or r.authorization_id not in self._authorizations
                    or r.readiness_id not in self._readiness or not r.lineage_id
                    or not r.audit_state or r.audit_state == GENESIS):
                out.append(aid)
        return sorted(out)

    def to_dict(self) -> dict:
        return {
            "security_registry_version": self.version, "counts": self.counts(),
            "users": {u: r.to_dict() for u, r in sorted(self._users.items())},
            "credentials": {c: r.to_dict() for c, r in sorted(self._credentials.items())},
            "sessions": {s: r.to_dict() for s, r in sorted(self._sessions.items())},
            "authentications": {a: r.to_dict() for a, r in sorted(self._authentications.items())},
            "authorizations": {a: r.to_dict() for a, r in sorted(self._authorizations.items())},
            "accesses": {a: r.to_dict() for a, r in sorted(self._accesses.items())},
            "readiness": {r_id: r.to_dict() for r_id, r in sorted(self._readiness.items())},
            "policies": self._policy_engine.to_dict() if self._policy_engine else {"n_policies": 0},
        }


__all__ = ["SecurityRegistry", "RegistryError"]
