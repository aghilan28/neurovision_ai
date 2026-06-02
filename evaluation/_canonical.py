"""Deterministic serialization, hashing, and seeding helpers for ``evaluation/``.

This is the evaluation layer's **own** self-contained utility. It deliberately
mirrors the small canonical-JSON/hashing helpers in ``datasets`` and
``preprocessing`` rather than importing a private symbol across a module boundary,
keeping each layer self-contained (see the V1-P3/P4 decision record on canonical
duplication). Depends on the Python standard library + NumPy only.

Everything here is deterministic: identical inputs always produce identical JSON,
hashes, fingerprints, and derived seeds — the foundation of reproducible
evaluation (AP-6, NR-10).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np


def canonical_json(obj: Any) -> str:
    """Serialize ``obj`` to a canonical, reproducible JSON string."""
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_json_bytes(obj: Any) -> bytes:
    return canonical_json(obj).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_fingerprint(obj: Any) -> str:
    """SHA-256 over the canonical JSON of ``obj`` (a content fingerprint)."""
    return sha256_hex(canonical_json_bytes(obj))


def mint_id(prefix: str, *parts: str, length: int = 16) -> str:
    """Mint a deterministic, content-derived identifier ``<prefix>-<hex[:length]>``."""
    if not prefix:
        raise ValueError("identifier prefix must be non-empty")
    if length <= 0 or length > 64:
        raise ValueError("identifier length must be in 1..64 hex chars")
    payload = "\n".join(parts).encode("utf-8")
    return f"{prefix}-{sha256_hex(payload)[:length]}"


def derive_seed(*parts: str, base_seed: int = 0) -> int:
    """Derive a deterministic 32-bit seed from string parts + an explicit base seed.

    Splitting must be deterministic *and* reproducible from recorded inputs: the
    same ``(parts, base_seed)`` always yields the same seed, so a split can be
    regenerated exactly (AP-3/AP-6, NR-9/NR-10). The base seed is always recorded
    in split metadata.
    """
    payload = f"{base_seed}\u0000" + "\u0000".join(parts)
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    # Take 4 bytes as an unsigned 32-bit integer (NumPy-friendly seed range).
    return int.from_bytes(digest[:4], "big")



def array_fingerprint(*arrays: np.ndarray) -> str:
    """Deterministic fingerprint over one or more arrays' shapes, dtypes, and bytes.

    Used to stamp metric/result provenance with the exact inputs that produced a
    value, so a reported metric is traceable and reproducible (AP-5/AP-6).
    """
    digest = hashlib.sha256()
    for array in arrays:
        contiguous = np.ascontiguousarray(array)
        digest.update(
            canonical_json_bytes(
                {"dtype": str(contiguous.dtype), "shape": list(contiguous.shape)}
            )
        )
        digest.update(contiguous.tobytes())
    return digest.hexdigest()
