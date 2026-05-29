"""Deterministic serialization, hashing, and identifier helpers for ``datasets/``.

Every artifact the data layer emits must be **deterministic** and **traceable**
(AP-3/AP-5/AP-6, NR-9/NR-10/NR-11). This module is the single, self-contained
source of:

* **Canonical JSON** — stable key ordering, fixed separators, no environment- or
  locale-dependent formatting. The byte output is reproducible across machines.
* **Content hashing** — SHA-256 over raw file bytes and over canonical JSON, used
  for checksums, content-addressed IDs, and dataset fingerprints.
* **Identifier minting** — deterministic, content-derived IDs so the *same* input
  always yields the *same* ID (enables duplicate detection, NR-8 traceability).

The module deliberately depends on the Python standard library only; it is the
data layer's own utility and is **not** shared across module boundaries (keeping
``preprocessing`` a pure leaf — see docs/architecture/DEPENDENCY_GRAPH.md).
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

# Stream files in fixed-size chunks so hashing is constant-memory and
# deterministic regardless of platform buffering.
_HASH_CHUNK_BYTES = 1 << 20  # 1 MiB


def canonical_json(obj: Any) -> str:
    """Serialize ``obj`` to a canonical, reproducible JSON string.

    Keys are sorted; separators are fixed; non-ASCII is escaped so the byte
    stream is identical on every platform. ``NaN``/``Infinity`` are rejected
    because they are not valid JSON and would undermine reproducibility.
    """
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_json_bytes(obj: Any) -> bytes:
    """UTF-8 bytes of :func:`canonical_json` (the hashing input)."""
    return canonical_json(obj).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """SHA-256 of ``data`` as a lowercase hex digest."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | os.PathLike[str]) -> str:
    """Streaming SHA-256 of a file's raw bytes as a lowercase hex digest."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_fingerprint(obj: Any) -> str:
    """SHA-256 over the canonical JSON of ``obj`` (a content fingerprint)."""
    return sha256_hex(canonical_json_bytes(obj))


def mint_id(prefix: str, *parts: str, length: int = 16) -> str:
    """Mint a deterministic, content-derived identifier.

    The identifier is ``"<prefix>-<hexdigest[:length]>"`` where the digest is
    SHA-256 over the newline-joined ``parts``. Identical inputs always produce
    the identical identifier, which is what makes duplicate detection and
    cross-artifact traceability deterministic.
    """
    if not prefix:
        raise ValueError("identifier prefix must be non-empty")
    if length <= 0 or length > 64:
        raise ValueError("identifier length must be in 1..64 hex chars")
    payload = "\n".join(parts).encode("utf-8")
    return f"{prefix}-{sha256_hex(payload)[:length]}"
