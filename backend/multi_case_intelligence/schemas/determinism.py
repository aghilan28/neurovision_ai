"""Deterministic identity primitives.

Everything that makes the intelligence and decision-support layers reproducible
(AP-3 Deterministic preprocessing, AP-6 Reproducibility) bottoms out here.

Hard rules enforced by construction in this module:

* **No wall-clock.** Nothing in this module (or anything built on it) reads the
  system clock. Ordering is provided by *logical* sequence numbers supplied by
  the caller, never by ``datetime.now()``.
* **No randomness.** There is no use of ``random``/``uuid``/hashing of object
  identity. Identifiers are *content addressed*: identical content always yields
  the identical identifier.
* **Canonical serialization.** Two values that are semantically equal serialize
  to byte-identical JSON, so their hashes match across processes and machines.

These are pure functions with no global mutable state.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

# Number of decimal places every floating point value is quantized to before it
# participates in a hash or is stored on an artifact. This removes float
# representation noise so that determinism holds across platforms.
FLOAT_NDIGITS = 9


def quantize(value: float, ndigits: int = FLOAT_NDIGITS) -> float:
    """Quantize a float to a fixed number of decimals (deterministic).

    ``-0.0`` is normalized to ``0.0`` and non-finite values are rejected, because
    a clinical-grade reproducible artifact may not contain NaN/inf.
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"quantize expects a real number, got {type(value)!r}")
    f = float(value)
    if not math.isfinite(f):
        raise ValueError(f"non-finite values are not permitted: {value!r}")
    r = round(f, ndigits)
    if r == 0.0:  # normalize -0.0 -> 0.0
        r = 0.0
    return r


def _canonicalize(obj: Any) -> Any:
    """Recursively convert ``obj`` into JSON-canonicalizable primitives.

    The conversion is total and deterministic for the value types used by this
    platform. Unsupported types raise ``TypeError`` rather than silently
    producing a non-reproducible representation.
    """
    if obj is None or isinstance(obj, (str, bool)):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        return quantize(obj)
    if isinstance(obj, Enum):
        return _canonicalize(obj.value)
    if is_dataclass(obj) and not isinstance(obj, type):
        return _canonicalize(asdict(obj))
    if isinstance(obj, Mapping):
        # Sort keys for canonical ordering; keys are coerced to str.
        return {str(k): _canonicalize(obj[k]) for k in sorted(obj, key=str)}
    if isinstance(obj, (set, frozenset)):
        # Sets are unordered -> sort their canonical form for stability.
        return sorted((_canonicalize(v) for v in obj), key=_sort_key)
    if isinstance(obj, (list, tuple)) or (
        isinstance(obj, Sequence) and not isinstance(obj, (str, bytes))
    ):
        return [_canonicalize(v) for v in obj]
    raise TypeError(f"cannot canonicalize value of type {type(obj)!r}")


def _sort_key(value: Any) -> str:
    """Stable sort key for canonicalized set members."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_json(obj: Any) -> str:
    """Return the canonical JSON string for ``obj``.

    Canonical means: keys sorted, no insignificant whitespace, ASCII-escaped,
    floats quantized. Semantically equal inputs always produce identical output.
    """
    return json.dumps(
        _canonicalize(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def content_hash(obj: Any) -> str:
    """Return the SHA-256 hex digest of the canonical JSON of ``obj``."""
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def short_hash(obj: Any, length: int = 16) -> str:
    """Return a truncated content hash, used inside human-readable IDs."""
    if length <= 0 or length > 64:
        raise ValueError("short hash length must be in 1..64")
    return content_hash(obj)[:length]


def deterministic_id(prefix: str, *parts: Any) -> str:
    """Construct a content-addressed identifier.

    The same ``prefix`` and ``parts`` always yield the same id; different
    content yields a different id with overwhelming probability. This is the only
    sanctioned way to mint an identifier in these subsystems (no UUIDs).
    """
    if not prefix or not prefix.isidentifier():
        raise ValueError(f"prefix must be a valid identifier token: {prefix!r}")
    return f"{prefix}-{short_hash(list(parts))}"


def hash_chain(prev_hash: str, payload: Any) -> str:
    """Compute the next hash in an append-only chain.

    ``prev_hash`` links each entry to its predecessor, making the chain
    tamper-evident: altering any earlier entry changes every subsequent hash.
    """
    return content_hash({"prev": prev_hash, "payload": _canonicalize(payload)})


# The canonical "genesis" link for a fresh hash chain.
GENESIS_HASH = "0" * 64
