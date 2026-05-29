"""``preprocessing/`` — DSP Layer (deterministic, versioned signal processing).

The leaf of the dependency DAG: imports nobody internal (NR-8). Provides the
single authoritative, deterministic path from raw EEG windows to model-ready
signal, plus the provenance primitives downstream layers reuse for hashing.

See ``preprocessing/README.md`` and docs/architecture/ for the boundary contract.
"""

from __future__ import annotations

from .version import PREPROCESSING_VERSION, PREPROCESSING_SPEC, preprocessing_version
from .pipeline import (
    PreprocessingConfig,
    transform,
    preprocessing_signature,
)
from ._provenance import canonical_json, hash_obj, hash_array, full_sha256

__all__ = [
    "PREPROCESSING_VERSION",
    "PREPROCESSING_SPEC",
    "preprocessing_version",
    "PreprocessingConfig",
    "transform",
    "preprocessing_signature",
    "canonical_json",
    "hash_obj",
    "hash_array",
    "full_sha256",
]
