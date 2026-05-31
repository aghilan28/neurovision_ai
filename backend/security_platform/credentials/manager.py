"""Credential protection (DRP5 credentials).

Registers, verifies, and rotates credentials **reusing** the platform's PBKDF2 password
hashing + injectable entropy source (``backend.application_backend.auth`` — no reinvented
crypto, NR-6). A credential stores a salted PBKDF2 hash + salt (verification material) and
**never** the plaintext password. Deterministic given a deterministic entropy source (so ids
reproduce); secure-by-default in production.
"""

from __future__ import annotations

from typing import Optional

from backend.application_backend.auth import (  # reuse: PBKDF2 + entropy (no reinvented crypto)
    hash_password, verify_password, EntropySource, DeterministicEntropy,
)
from backend.application_backend.version import PBKDF2_ITERATIONS

from ..identity import mint_identity
from ..models.domain import CredentialRecord, CredentialStatus
from ..version import DETERMINISTIC_EPOCH, SALT_BYTES


class CredentialError(ValueError):
    """Raised on an invalid credential request (never reveals secret material)."""


class CredentialManager:
    """Issues + verifies + rotates salted PBKDF2 credentials (no plaintext storage)."""

    algorithm = "pbkdf2_hmac_sha256"

    def __init__(self, entropy: Optional[EntropySource] = None, *,
                 iterations: int = PBKDF2_ITERATIONS):
        # deterministic by default *here* so the security flow reproduces in tests/verify;
        # production injects SecureEntropy.
        self.entropy = entropy or DeterministicEntropy("neurovision-drp5")
        self.iterations = iterations

    def register(self, user_id: str, password: str, *,
                 created_at: str = DETERMINISTIC_EPOCH) -> CredentialRecord:
        if not password:
            raise CredentialError("password must be a non-empty string")
        salt = self.entropy(SALT_BYTES)
        salt_hex = salt.hex()
        hash_hex = hash_password(password, salt, iterations=self.iterations)
        credential_id = mint_identity("credential", {"user_id": user_id, "hash_hex": hash_hex}).id
        return CredentialRecord(
            credential_id=credential_id, user_id=user_id, algorithm=self.algorithm,
            iterations=self.iterations, salt_hex=salt_hex, hash_hex=hash_hex,
            status=CredentialStatus.ACTIVE, created_at=created_at)

    def verify(self, credential: CredentialRecord, password: str) -> bool:
        if credential.status != CredentialStatus.ACTIVE:
            return False
        return verify_password(password, credential.salt_hex, credential.hash_hex,
                               iterations=credential.iterations)

    def rotate(self, credential: CredentialRecord, new_password: str, *,
               created_at: str = DETERMINISTIC_EPOCH) -> tuple[CredentialRecord, CredentialRecord]:
        """Return (rotated_old, new_active) — the old credential is marked ROTATED."""
        import dataclasses
        rotated_old = dataclasses.replace(credential, status=CredentialStatus.ROTATED)
        new_active = self.register(credential.user_id, new_password, created_at=created_at)
        return rotated_old, new_active

    def revoke(self, credential: CredentialRecord) -> CredentialRecord:
        import dataclasses
        return dataclasses.replace(credential, status=CredentialStatus.REVOKED)


__all__ = ["CredentialManager", "CredentialError"]
