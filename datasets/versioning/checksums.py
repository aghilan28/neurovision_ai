"""Checksum helpers.

Thin, clearly-named wrappers over the canonical SHA-256 utilities so that
"checksum" intent is explicit at call sites in the versioning subsystem.
"""

from __future__ import annotations

import os

from datasets._canonical import sha256_file, sha256_hex


def checksum_file(path: str | os.PathLike[str]) -> str:
    """SHA-256 hex digest of a file's raw bytes."""
    return sha256_file(path)


def checksum_bytes(data: bytes) -> str:
    """SHA-256 hex digest of a byte string."""
    return sha256_hex(data)


def verify_checksum(path: str | os.PathLike[str], expected_sha256: str) -> bool:
    """True iff the file's content hash equals ``expected_sha256`` (case-insensitive)."""
    return checksum_file(path).lower() == expected_sha256.strip().lower()
