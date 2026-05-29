"""Provenance, hashing and content-addressing for the ML layer.

Reuses the DSP leaf's deterministic hashing (``ml`` → ``preprocessing`` is an
allowed edge, NR-8) and adds ML-level helpers: content-addressed identifiers
(lineage IDs, benchmark IDs) and canonical JSON file IO.

All identifiers are *content-derived*, never time-derived, so the same logical
content always yields the same ID — the basis of reproducible, auditable lineage
(AP-5 / AP-6 / NR-10 / NR-11).
"""

from __future__ import annotations

import json
import os
from typing import Any

import numpy as np

from preprocessing import canonical_json, hash_obj, hash_array, full_sha256  # allowed edge

__all__ = [
    "canonical_json",
    "hash_obj",
    "hash_array",
    "full_sha256",
    "content_id",
    "write_json",
    "read_json",
    "sha256_of_file",
]


def content_id(prefix: str, payload: Any) -> str:
    """Return a stable, prefixed content identifier (e.g. ``lineage@...``).

    The identifier is a function of ``payload`` only, so re-running with the same
    inputs reproduces the same ID.
    """
    return f"{prefix}+{hash_obj(payload)}"


def write_json(path: str, obj: Any) -> str:
    """Write ``obj`` as canonical JSON to ``path`` and return its sha256 checksum.

    Canonical (sorted, compact) so the on-disk bytes are deterministic and the
    checksum is reproducible (artifact integrity, NR-10).
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    data = canonical_json(obj).encode("utf-8")
    with open(path, "wb") as fh:
        fh.write(data)
    return full_sha256(data)


def read_json(path: str) -> Any:
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def sha256_of_file(path: str) -> str:
    """Return the full sha256 of a file's bytes (artifact integrity check)."""
    with open(path, "rb") as fh:
        return full_sha256(fh.read())
