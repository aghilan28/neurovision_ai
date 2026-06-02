"""Deterministic serialization, hashing, and array-fingerprinting for ``preprocessing/``.

This is the DSP layer's **own** self-contained utility. It deliberately duplicates
the small canonical-JSON/hashing helpers found in ``datasets/`` rather than sharing
them, because ``preprocessing`` must remain a pure leaf that imports **no** internal
module (docs/architecture/IMPORT_RULES.md, Rule NR-8). The duplication is a few
dozen lines and is the correct trade-off for keeping the dependency graph acyclic.

Depends on the Python standard library + NumPy only.
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


def array_fingerprint(array: np.ndarray) -> str:
    """Deterministic fingerprint of a NumPy array's shape, dtype, and bytes.

    Used to fingerprint signal/window arrays for lineage and reproducibility
    checks. The array is made C-contiguous so the byte layout is canonical; the
    dtype string and shape are included so arrays differing only in metadata
    fingerprint differently. Given a pinned environment, identical computations
    produce identical fingerprints (AP-6).
    """
    contiguous = np.ascontiguousarray(array)
    header = canonical_json_bytes(
        {"dtype": str(contiguous.dtype), "shape": list(contiguous.shape)}
    )
    digest = hashlib.sha256()
    digest.update(header)
    digest.update(contiguous.tobytes())
    return digest.hexdigest()
