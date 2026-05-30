"""Password hashing — secure-by-default, deterministic given a salt (P6-C).

Uses the stdlib ``hashlib.pbkdf2_hmac('sha256', ...)`` (a slow, salted KDF). The salt
is supplied by the caller (from a secure entropy source by default; a deterministic
source in tests). Given the *same* salt + password the derived hash is reproducible,
which is what lets the auth tests be deterministic without weakening the default
(random-salt) configuration. Verification is constant-time (``hmac.compare_digest``).
"""

from __future__ import annotations

import hashlib
import hmac

from ..version import PBKDF2_ITERATIONS


def hash_password(password: str, salt: bytes, *, iterations: int = PBKDF2_ITERATIONS) -> str:
    """Return the hex PBKDF2-HMAC-SHA256 digest of ``password`` under ``salt``."""
    if not isinstance(password, str) or password == "":
        raise ValueError("password must be a non-empty string")
    if not isinstance(salt, (bytes, bytearray)) or len(salt) == 0:
        raise ValueError("salt must be non-empty bytes")
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes(salt), iterations)
    return dk.hex()


def verify_password(password: str, salt_hex: str, expected_hash_hex: str, *,
                    iterations: int = PBKDF2_ITERATIONS) -> bool:
    """Constant-time check that ``password`` reproduces ``expected_hash_hex``."""
    if not isinstance(password, str) or password == "":
        return False
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    candidate = hash_password(password, salt, iterations=iterations)
    return hmac.compare_digest(candidate, expected_hash_hex)


__all__ = ["hash_password", "verify_password"]
