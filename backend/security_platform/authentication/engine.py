"""Authentication engine (DRP5-C).

Verifies a credential and issues/validates/revokes sessions, **reusing** the platform's
token generation + fingerprinting (``backend.application_backend.auth`` — NR-6). A session
stores only a token *fingerprint* (never the raw token); expiry is a deterministic logical
window (no wall-clock). Deterministic, versioned, traceable; no plaintext credential storage.
"""

from __future__ import annotations

from typing import Optional

from backend.application_backend.auth import (  # reuse: token gen + fingerprint
    EntropySource, DeterministicEntropy, generate_token, token_fingerprint,
)

from ..credentials import CredentialManager
from ..identity import mint_identity
from ..models.domain import (
    AuthenticationRecord, AuthOutcome, CredentialRecord, SessionRecord, SessionStatus,
)
from ..version import DETERMINISTIC_EPOCH, DEFAULT_SESSION_TTL_STEPS, SESSION_TOKEN_BYTES


class AuthenticationEngine:
    """Credential verification + session lifecycle."""

    def __init__(self, credential_manager: Optional[CredentialManager] = None,
                 entropy: Optional[EntropySource] = None):
        self.credentials = credential_manager or CredentialManager()
        self.entropy = entropy or DeterministicEntropy("neurovision-drp5-sessions")

    def authenticate(self, user_id: str, credential: CredentialRecord, password: str, *,
                     issued_step: int = 0, ttl_steps: int = DEFAULT_SESSION_TTL_STEPS,
                     created_at: str = DETERMINISTIC_EPOCH
                     ) -> tuple[AuthenticationRecord, Optional[SessionRecord]]:
        """Verify the credential; on success issue a session. Never raises on bad password."""
        ok = self.credentials.verify(credential, password)
        if not ok:
            auth_id = mint_identity("authentication", {
                "credential_id": credential.credential_id, "outcome": AuthOutcome.FAILURE.value}).id
            return (AuthenticationRecord(
                authentication_id=auth_id, user_id=user_id, credential_id=credential.credential_id,
                session_id=None, outcome=AuthOutcome.FAILURE, reason="invalid_credentials",
                created_at=created_at), None)

        token = generate_token(self.entropy, nbytes=SESSION_TOKEN_BYTES)
        fp = token_fingerprint(token)
        session_id = mint_identity("security_session", {
            "credential_id": credential.credential_id, "token_fingerprint": fp}).id
        session = SessionRecord(
            session_id=session_id, user_id=user_id, credential_id=credential.credential_id,
            token_fingerprint=fp, status=SessionStatus.ACTIVE, issued_step=issued_step,
            ttl_steps=ttl_steps, created_at=created_at)
        auth_id = mint_identity("authentication", {
            "credential_id": credential.credential_id, "outcome": AuthOutcome.SUCCESS.value}).id
        auth = AuthenticationRecord(
            authentication_id=auth_id, user_id=user_id, credential_id=credential.credential_id,
            session_id=session_id, outcome=AuthOutcome.SUCCESS, reason="ok", created_at=created_at)
        return auth, session

    def validate_session(self, session: SessionRecord, *, at_step: int = 0) -> tuple[bool, str]:
        """Return (valid, reason). A session is valid iff ACTIVE and within its logical TTL."""
        if session.status == SessionStatus.REVOKED:
            return False, "revoked"
        if session.status == SessionStatus.EXPIRED:
            return False, "expired"
        if at_step > session.expires_step():
            return False, "expired"
        return True, "ok"

    def effective_status(self, session: SessionRecord, *, at_step: int = 0) -> SessionStatus:
        if session.status != SessionStatus.ACTIVE:
            return session.status
        return SessionStatus.ACTIVE if at_step <= session.expires_step() else SessionStatus.EXPIRED

    def revoke_session(self, session: SessionRecord) -> SessionRecord:
        import dataclasses
        return dataclasses.replace(session, status=SessionStatus.REVOKED)


__all__ = ["AuthenticationEngine"]
