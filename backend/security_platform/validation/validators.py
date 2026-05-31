"""Security content validation (DRP5-J, build-time).

Validates credential / session / authorization / policy / version integrity, producing
structured ``(name, passed, detail)`` results — pure functions, no exceptions, never revealing
secret material.
"""

from __future__ import annotations

from ..models.domain import (
    AccessDecision, AuthOutcome,
)


class SecurityContentValidator:
    """Build-time validation of the security records."""

    def credential_integrity(self, credential) -> tuple[str, bool, dict]:
        ok = (bool(credential.hash_hex) and bool(credential.salt_hex) and credential.iterations > 0
              and credential.algorithm == "pbkdf2_hmac_sha256")
        # never store/echo plaintext; only confirm a hash exists
        return ("credential_integrity", bool(ok),
                {"algorithm": credential.algorithm, "iterations": credential.iterations,
                 "has_plaintext": False})

    def session_integrity(self, session, authentication) -> tuple[str, bool, dict]:
        ok = (bool(session.token_fingerprint) and session.ttl_steps > 0
              and session.credential_id == authentication.credential_id
              and authentication.outcome == AuthOutcome.SUCCESS)
        return ("session_integrity", bool(ok), {"status": session.status.value})

    def authorization_integrity(self, authorization) -> tuple[str, bool, dict]:
        ok = authorization.decision in (AccessDecision.PERMITTED, AccessDecision.DENIED)
        if authorization.decision == AccessDecision.PERMITTED:
            ok = ok and len(authorization.matched_policies) > 0   # explicit permission only
        return ("authorization_integrity", bool(ok),
                {"decision": authorization.decision.value,
                 "matched_policies": len(authorization.matched_policies)})

    def policy_integrity(self, policy_engine) -> tuple[str, bool, dict]:
        ok, problems = policy_engine.validate()
        return ("policy_integrity", bool(ok and len(policy_engine.list_policies()) > 0),
                {"n_policies": len(policy_engine.list_policies()), "problems": problems})

    def version_integrity(self, version_str: str) -> tuple[str, bool, dict]:
        return ("version_integrity", bool(version_str) and len(version_str) == 16,
                {"version": version_str})

    def content_checks(self, *, credential, session, authentication, authorization,
                       policy_engine) -> list[tuple]:
        return [
            self.credential_integrity(credential),
            self.session_integrity(session, authentication),
            self.authorization_integrity(authorization),
            self.policy_integrity(policy_engine),
        ]


__all__ = ["SecurityContentValidator"]
