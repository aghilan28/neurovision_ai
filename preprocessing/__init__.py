"""``preprocessing/`` — DSP Layer (deterministic, versioned signal processing).

The leaf of the dependency DAG: imports nobody internal (NR-8). Provides the
single authoritative, deterministic path from raw EEG windows to model-ready
signal, plus the provenance primitives downstream layers reuse for hashing.

See ``preprocessing/README.md`` and docs/architecture/ for the boundary contract.
"""``preprocessing/`` — DSP Layer (Version 1).

The **deterministic, versioned signal-processing foundation** of NeuroVision AI
and the leaf of the dependency graph: it imports **no internal module** (only
pinned third-party numeric/DSP libraries — NumPy/SciPy). Everything above inherits
its reproducibility (AP-3/AP-6, NR-9/NR-10).

It transforms a raw EEG signal representation into standardized, windowed signal
suitable for downstream consumers, recording **every transformation** so the
result is auditable and reproducible. Future models consume these standardized
outputs and never need to know how preprocessing works internally.

Pipeline stages (each independently testable):

    input validation -> channel validation -> resampling -> filtering ->
    montage -> normalization -> window generation -> output validation ->
    artifact (quality) reporting -> lineage recording

Boundary contract (docs/architecture/IMPORT_RULES.md): imports nobody internal;
never introduces nondeterminism on the production path (NR-9).
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
#: Version of the preprocessing subsystem as a whole. Recorded on every artifact
#: and lineage record. Changed only via a recorded governance decision (NR-5).
PREPROCESSING_VERSION = "1.0.0"

__all__ = ["PREPROCESSING_VERSION"]
