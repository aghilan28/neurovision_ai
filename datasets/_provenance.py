"""Provenance helpers for the datasets module.

Reuses the DSP leaf's deterministic hashing (``datasets`` → ``preprocessing`` is
an allowed edge). Keeping a thin re-export here makes call sites read naturally
while honouring the dependency direction.
"""

from __future__ import annotations

from preprocessing import canonical_json, hash_obj, hash_array  # allowed: datasets -> preprocessing

__all__ = ["canonical_json", "hash_obj", "hash_array"]
