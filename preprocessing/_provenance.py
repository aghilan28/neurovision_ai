"""Deterministic hashing / canonicalization helpers for the DSP leaf.

These are intentionally tiny and dependency-free (stdlib + numpy only). The DSP
layer imports nobody internal (NR-8), so it carries its own minimal provenance
utilities rather than sharing a higher-level module.

Hashes are content-addressed: the same logical content always produces the same
digest, which is the basis of artifact integrity and reproducibility checks
(AP-6 / NR-10).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np

# Short, stable digest length for embedding in identifiers / lineage records.
_DIGEST_CHARS = 16


def canonical_json(obj: Any) -> str:
    """Serialize ``obj`` to a canonical JSON string (sorted keys, no whitespace).

    Canonicalization guarantees that semantically identical structures hash
    identically regardless of key ordering.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=_default)


def _default(obj: Any) -> Any:
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    raise TypeError(f"Object of type {type(obj)!r} is not JSON-serializable")


def hash_obj(obj: Any) -> str:
    """Return a stable short sha256 digest of an arbitrary JSON-able object."""
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()[:_DIGEST_CHARS]


def hash_array(array: np.ndarray) -> str:
    """Return a stable sha256 digest of a numpy array's dtype, shape and bytes.

    Uses C-contiguous bytes so the digest is independent of memory layout.
    """
    arr = np.ascontiguousarray(array)
    hasher = hashlib.sha256()
    hasher.update(str(arr.dtype).encode("utf-8"))
    hasher.update(str(arr.shape).encode("utf-8"))
    hasher.update(arr.tobytes())
    return hasher.hexdigest()[:_DIGEST_CHARS]


def full_sha256(data: bytes) -> str:
    """Return the full sha256 hex digest of raw bytes (for artifact checksums)."""
    return hashlib.sha256(data).hexdigest()
