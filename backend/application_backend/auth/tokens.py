"""Entropy sources + session-token generation/validation (P6-C).

Secrets (salts, session tokens) are the only non-deterministic inputs in the
subsystem. They come from an injectable :class:`EntropySource`:

* the default :class:`SecureEntropy` wraps ``secrets.token_bytes`` (secure default);
* :class:`DeterministicEntropy` derives a reproducible byte stream from a seed via a
  SHA-256 counter, so tests can assert exact ids/tokens.

A token is opaque hex; only its **fingerprint** (a content hash) is ever stored, so a
leaked store cannot reveal a live token. ``token_fingerprint`` is what the session
identity is content-addressed from.
"""

from __future__ import annotations

import hashlib
import secrets

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import TOKEN_BYTES


class EntropySource:
    """Abstract entropy source returning ``nbytes`` of bytes."""

    def __call__(self, nbytes: int) -> bytes:  # pragma: no cover - interface
        raise NotImplementedError


class SecureEntropy(EntropySource):
    """Cryptographically secure entropy (the production default)."""

    def __call__(self, nbytes: int) -> bytes:
        return secrets.token_bytes(nbytes)


class DeterministicEntropy(EntropySource):
    """Reproducible entropy for tests/verification (seeded SHA-256 counter).

    NOT for production use — it exists only so the auth flow can be asserted
    bit-for-bit. It is never the default.
    """

    def __init__(self, seed: str = "neurovision-p6"):
        self._seed = seed.encode("utf-8")
        self._counter = 0

    def __call__(self, nbytes: int) -> bytes:
        out = bytearray()
        while len(out) < nbytes:
            block = hashlib.sha256(self._seed + self._counter.to_bytes(8, "big")).digest()
            out.extend(block)
            self._counter += 1
        return bytes(out[:nbytes])


def generate_token(entropy: EntropySource, *, nbytes: int = TOKEN_BYTES) -> str:
    """Return a fresh opaque hex token from ``entropy``."""
    return entropy(nbytes).hex()


def token_fingerprint(token: str) -> str:
    """Return the content fingerprint of a token (what gets stored, never the token)."""
    return hash_obj({"token": token})


__all__ = [
    "EntropySource", "SecureEntropy", "DeterministicEntropy",
    "generate_token", "token_fingerprint",
]
