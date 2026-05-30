"""AuthService — local authentication foundation (P6-C).

Implements user registration, login, and session create/validate/revoke on top of
:class:`UserService`. Passwords are stored only as salted PBKDF2 hashes in the private
credential store; sessions store only a token *fingerprint* (never the raw token).
Secrets come from an injectable entropy source (secure by default; deterministic in
tests). Every authentication event is appended to an immutable, tamper-evident audit
log and every session is a lineage node parented on its user node.

Local authentication only — no social login, no OAuth providers (out of scope).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ml.lineage import LineageTracker

from ..version import DETERMINISTIC_EPOCH, PBKDF2_ITERATIONS, SALT_BYTES
from ..identity import mint_identity
from ..models.domain import (
    BackendRegistryRecord, BackendVersion, EntityKind, SessionRecord, SessionStatus,
    UserRecord, UserStatus,
)
from ..audit import make_backend_audit_log, ImmutableAuditLog
from ..lineage import make_session_lineage
from ..registry import BackendRegistry
from ..storage import CredentialRecord, CredentialStore, make_session_store
from ..users import UserService
from .passwords import hash_password, verify_password
from .tokens import EntropySource, SecureEntropy, generate_token, token_fingerprint


class AuthError(RuntimeError):
    """Raised when authentication fails (kept deliberately non-specific to callers)."""


@dataclass(frozen=True)
class LoginResult:
    """The outcome of a successful login: the session + the one-time raw token."""

    session: SessionRecord
    token: str

    def to_dict(self) -> dict:
        # The raw token is intentionally omitted from the serialized form.
        return {"session": self.session.to_dict(), "token_present": bool(self.token)}


class AuthService:
    """Stateful service: credential store, session store, per-session audit logs."""

    def __init__(self, *, users: UserService, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[BackendRegistry] = None,
                 entropy: Optional[EntropySource] = None, iterations: int = PBKDF2_ITERATIONS):
        self.users = users
        self.lineage = lineage_tracker or users.lineage
        self.registry = registry or users.registry
        self.entropy = entropy or SecureEntropy()
        self.iterations = iterations
        self.credentials = CredentialStore()
        self.sessions = make_session_store()
        self._session_by_tfp: dict[str, str] = {}
        self._session_audit_logs: dict[str, ImmutableAuditLog] = {}

    # --- accessors ------------------------------------------------------------
    def audit_log_for(self, session_id: str) -> ImmutableAuditLog:
        return self._session_audit_logs[session_id]

    def get_session(self, session_id: str) -> SessionRecord:
        return self.sessions.get(session_id)

    def list_sessions(self) -> list[SessionRecord]:
        return self.sessions.values()

    # --- registration ---------------------------------------------------------
    def register(self, *, username: str, password: str, roles=None, metadata: Optional[dict] = None,
                 owner: str = "application-ops", created_at: str = DETERMINISTIC_EPOCH) -> UserRecord:
        """Register a new local user + store a salted password hash."""
        if not isinstance(password, str) or len(password) < 8:
            raise AuthError("password must be at least 8 characters")
        kwargs = {} if roles is None else {"roles": roles}
        user = self.users.create_user(username=username, metadata=metadata, owner=owner,
                                       created_at=created_at, **kwargs)
        salt = self.entropy(SALT_BYTES)
        digest = hash_password(password, salt, iterations=self.iterations)
        self.credentials.put(CredentialRecord(
            user_id=user.user_id, salt_hex=salt.hex(), hash_hex=digest, iterations=self.iterations))
        # Audit credential creation on the user's log WITHOUT any secret material.
        self.users.audit_log_for(user.user_id).append(
            "user_credentials_set", {"user_id": user.user_id, "algorithm": "pbkdf2_hmac_sha256",
                                     "iterations": self.iterations}, created_at=created_at)
        return user

    # --- login ----------------------------------------------------------------
    def login(self, *, username: str, password: str,
              created_at: str = DETERMINISTIC_EPOCH) -> LoginResult:
        """Authenticate credentials and create a new active session."""
        user = self.users.get_by_username(username)
        cred = self.credentials.get(user.user_id) if user else None
        # Verify even on unknown user is skipped, but keep the error non-specific.
        if user is None or cred is None or not verify_password(
                password, cred.salt_hex, cred.hash_hex, iterations=cred.iterations):
            raise AuthError("invalid username or password")
        if user.status != UserStatus.ACTIVE:
            raise AuthError("user account is not active")

        token = generate_token(self.entropy)
        tfp = token_fingerprint(token)
        identity_obj = mint_identity("session", {"user_id": user.user_id, "session_key": tfp})
        session_id = identity_obj.id

        node = self.lineage.record(make_session_lineage(
            session_id, user.user_id, user.lineage_id, created_at=created_at))
        log = make_backend_audit_log()
        self._session_audit_logs[session_id] = log
        log.append("session_created", {"session_id": session_id, "user_id": user.user_id,
                                       "token_fingerprint": tfp, "lineage_id": node.lineage_id},
                   created_at=created_at)

        session = self._assemble_session(
            session_id=session_id, user_id=user.user_id, token_fingerprint=tfp,
            status=SessionStatus.ACTIVE, previous=None, reason="created",
            created_at=created_at, lineage_id=node.lineage_id, log=log)
        self._store_session(session)
        self._session_by_tfp[tfp] = session_id
        return LoginResult(session=session, token=token)

    # --- validation -----------------------------------------------------------
    def validate_session(self, token: str) -> Optional[SessionRecord]:
        """Return the active session for ``token`` or ``None`` (no exception)."""
        if not isinstance(token, str) or token == "":
            return None
        session_id = self._session_by_tfp.get(token_fingerprint(token))
        if session_id is None:
            return None
        session = self.sessions.find(session_id)
        if session is None or session.status != SessionStatus.ACTIVE:
            return None
        if not self.users.exists(session.user_id):
            return None
        if self.users.get_user(session.user_id).status != UserStatus.ACTIVE:
            return None
        return session

    def authenticate(self, token: str) -> tuple[SessionRecord, UserRecord]:
        """Validate ``token`` and return (session, user) or raise ``AuthError``."""
        session = self.validate_session(token)
        if session is None:
            raise AuthError("invalid or expired session")
        return session, self.users.get_user(session.user_id)

    # --- revocation -----------------------------------------------------------
    def revoke_session(self, *, token: Optional[str] = None, session_id: Optional[str] = None,
                       created_at: str = DETERMINISTIC_EPOCH) -> SessionRecord:
        """Revoke a session (by raw token or by session id)."""
        if session_id is None and token is not None:
            session_id = self._session_by_tfp.get(token_fingerprint(token))
        if session_id is None or not self.sessions.exists(session_id):
            raise AuthError("unknown session")
        current = self.sessions.get(session_id)
        if current.status == SessionStatus.REVOKED:
            return current
        log = self._session_audit_logs[session_id]
        log.append("session_revoked", {"session_id": session_id, "user_id": current.user_id},
                   created_at=created_at)
        session = self._assemble_session(
            session_id=session_id, user_id=current.user_id,
            token_fingerprint=current.token_fingerprint, status=SessionStatus.REVOKED,
            previous=current.version.version, reason="revoked", created_at=created_at,
            lineage_id=current.lineage_id, log=log)
        self._store_session(session, allow_update=True)
        return session

    # --- internals ------------------------------------------------------------
    def _assemble_session(self, *, session_id, user_id, token_fingerprint, status, previous,
                          reason, created_at, lineage_id, log: ImmutableAuditLog) -> SessionRecord:
        state_sig = SessionRecord.state_signature_of(
            session_id=session_id, user_id=user_id, token_fingerprint=token_fingerprint, status=status)
        version = BackendVersion(version=BackendVersion.compute(state_sig, previous),
                                 previous=previous, reason=reason, created_at=created_at)
        log.append("session_version_changed", {"version": version.version, "reason": reason},
                   created_at=created_at)
        return SessionRecord(
            session_id=session_id, user_id=user_id, token_fingerprint=token_fingerprint,
            status=status, version=version, created_at=created_at, lineage_id=lineage_id,
            audit_head=log.head)

    def _store_session(self, session: SessionRecord, *, allow_update: bool = False) -> None:
        self.sessions.put(session, allow_update=allow_update)
        self.registry.register(BackendRegistryRecord(
            entity_kind=EntityKind.SESSION, entity_id=session.session_id, status=session.status.value,
            version=session.version.version, owner=session.user_id, creation_date=session.created_at,
            audit_state=session.audit_head or "", lineage_id=session.lineage_id or "",
            user_id=session.user_id, dependencies=(session.user_id,)))


__all__ = ["AuthService", "AuthError", "LoginResult"]
