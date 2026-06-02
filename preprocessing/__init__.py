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

#: Version of the preprocessing subsystem as a whole. Recorded on every artifact
#: and lineage record. Changed only via a recorded governance decision (NR-5).
PREPROCESSING_VERSION = "1.0.0"

__all__ = ["PREPROCESSING_VERSION"]
