"""Tiny stdlib helpers for the frontend (deterministic; no domain imports, NR-8).

The frontend may not import ``ml.provenance`` (that is a domain module), so it computes
its own deterministic content fingerprints with the standard library only. Identical
inputs always yield the same fingerprint, keeping rendered state/reports reproducible.
"""

from __future__ import annotations

import hashlib
import html
import json
from typing import Any


def canonical_json(obj: Any) -> str:
    """Deterministic JSON encoding (sorted keys, compact separators)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def fingerprint(obj: Any, *, n: int = 16) -> str:
    """A short, stable content fingerprint of any JSON-able object."""
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()[:n]


def esc(value: Any) -> str:
    """HTML-escape a value for safe static rendering (no JS, no injection)."""
    return html.escape("" if value is None else str(value), quote=True)


__all__ = ["canonical_json", "fingerprint", "esc"]
