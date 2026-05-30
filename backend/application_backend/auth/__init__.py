"""``backend/application_backend/auth`` — local authentication foundation (P6-C).

Registration, login, session create/validate/revoke, password hashing (PBKDF2), and
token generation/validation. Secure defaults with an injectable entropy source for
deterministic tests. Local authentication only (no social login / OAuth providers).
"""

from __future__ import annotations

from .passwords import hash_password, verify_password
from .tokens import (
    EntropySource, SecureEntropy, DeterministicEntropy, generate_token, token_fingerprint,
)
from .service import AuthService, AuthError, LoginResult

__all__ = [
    "hash_password", "verify_password",
    "EntropySource", "SecureEntropy", "DeterministicEntropy", "generate_token", "token_fingerprint",
    "AuthService", "AuthError", "LoginResult",
]
