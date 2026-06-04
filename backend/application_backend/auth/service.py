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
        # PART 1 + PART 2: Both indexes are initialized unconditionally at construction
        # so they exist regardless of whether persistence or recovery runs.
        self._session_by_tfp: dict[str, str] = {}
        self._session_audit_logs: dict[str, ImmutableAuditLog] = {}

    # --- PART 2: session index rehydration ------------------------------------
    def rehydrate_session_index(self) -> None:
        """Rebuild the token-fingerprint -> session-id index from the session store.

        Scans every session record in the persistent session store and rebuilds the
        in-memory ``_session_by_tfp`` lookup so that ``validate_session()`` can resolve
        tokens issued before a restart/deployment/recovery.

        Also rebuilds ``_session_audit_logs`` entries for sessions that have no
        corresponding audit log (creates a fresh audit log so ``revoke_session`` and
        ``audit_log_for`` do not crash on recovered sessions).

        This method is idempotent: calling it multiple times produces the same index.
        """
        for sess in self.sessions.values():
            self._session_by_tfp[sess.token_fingerprint] = sess.session_id
            if sess.session_id not in self._session_audit_logs:
                log = make_backend_audit_log()
                log.append("session_recovered", {
                    "session_id": sess.session_id,
                    "user_id": sess.user_id,
                    "token_fingerprint": sess.token_fingerprint,
                    "status": sess.status.value,
                }, created_at=sess.created_at)
                self._session_audit_logs[sess.session_id] = log

    # Backward-compatible alias used by existing callers.
    def rehydrate_tfp_index(self) -> None:
        """Alias for :meth:`rehydrate_session_index` (backward compatibility)."""
        self.rehydrate_session_index()

    # --- accessors ------------------------------------------------------------
    def audit_log_for(self, session_id: str) -> ImmutableAuditLog:
        if session_id not in self._session_audit_logs:
            # Defensive: if a session exists but its audit log was lost (e.g. recovery),
            # create a minimal audit log rather than crashing.
            log = make_backend_audit_log()
            log.append("audit_log_reconstructed", {"session_id": session_id},
                       created_at=DETERMINISTIC_EPOCH)
            self._session_audit_logs[session_id] = log
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

    # --- PART 3: hardened session validation -----------------------------------
    def validate_session(self, token: str) -> Optional[SessionRecord]:
        """Return the active session for ``token`` or ``None`` (no exception).

        PART 3 hardening: if the in-memory ``_session_by_tfp`` index does not contain
        the fingerprint, fall back to a linear scan of the session store. If a match
        is found, the index is repaired on the fly so subsequent lookups are O(1).
        This ensures validation survives index loss from restart/deployment/recovery.
        """
        if not isinstance(token, str) or token == "":
            return None
        from .tokens import token_fingerprint as _tfp
        tfp = _tfp(token)

        # Primary lookup: O(1) index.
        session_id = self._session_by_tfp.get(tfp)

        # PART 3: fallback — scan the authoritative session store and repair the index.
        if session_id is None:
            for sess in self.sessions.values():
                if sess.token_fingerprint == tfp:
                    session_id = sess.session_id
                    # Repair the index so future lookups are O(1).
                    self._session_by_tfp[tfp] = session_id
                    break

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

    def classify_session_token(self, token: str) -> tuple[str, Optional[SessionRecord]]:
        """Read-only classification of an opaque session ``token`` (DBE-5 hardening).

        Returns ``(state, session)`` where ``state`` is one of:

        * ``"active"``        — a live, ACTIVE session for an ACTIVE user;
        * ``"revoked"``       — the token maps to a session that is no longer ACTIVE;
        * ``"inactive_user"`` — the session is ACTIVE but its user is not ACTIVE;
        * ``"unknown"``       — the token matches no issued session (or is empty/non-string).

        Purely additive and side-effect-free: it issues nothing, mutates no state, and
        **never raises** — it only reads the existing session/user stores so the HTTP
        boundary can classify an invalid token into a controlled response instead of
        crashing. Distinguishing ``revoked`` from ``unknown`` is why this is richer than
        :meth:`validate_session` (which returns ``None`` for both).
        """
        if not isinstance(token, str) or token == "":
            return "unknown", None
        try:
            tfp = token_fingerprint(token)
        except Exception:  # noqa: BLE001 — never raise from classification
            return "unknown", None
        session_id = self._session_by_tfp.get(tfp)
        if session_id is None:
            for sess in self.sessions.values():
                if sess.token_fingerprint == tfp:
                    session_id = sess.session_id
                    self._session_by_tfp[tfp] = session_id
                    break
        if session_id is None:
            return "unknown", None
        session = self.sessions.find(session_id)
        if session is None:
            return "unknown", None
        if session.status != SessionStatus.ACTIVE:
            return "revoked", session
        if not self.users.exists(session.user_id):
            return "unknown", session
        if self.users.get_user(session.user_id).status != UserStatus.ACTIVE:
            return "inactive_user", session
        return "active", session

    # --- revocation -----------------------------------------------------------
    def revoke_session(self, *, token: Optional[str] = None, session_id: Optional[str] = None,
                       created_at: str = DETERMINISTIC_EPOCH) -> SessionRecord:
        """Revoke a session (by raw token or by session id)."""
        if session_id is None and token is not None:
            tfp = token_fingerprint(token)
            session_id = self._session_by_tfp.get(tfp)
            if session_id is None:
                for sess in self.sessions.values():
                    if sess.token_fingerprint == tfp:
                        session_id = sess.session_id
                        self._session_by_tfp[tfp] = session_id
                        break
        if session_id is None or not self.sessions.exists(session_id):
            raise AuthError("unknown session")
        current = self.sessions.get(session_id)
        if current.status == SessionStatus.REVOKED:
            return current
        log = self.audit_log_for(session_id)
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
