"""Version identity for the deterministic preprocessing (DSP) layer.

The preprocessing version is provenance (AP-5) and the anchor of reproducibility
(AP-3 / AP-6): identical inputs + identical preprocessing version always yield
identical outputs (NR-9). Any change to the transform semantics MUST bump this
version, because downstream lineage records pin against it.

This module is part of the DSP leaf and imports nobody internal (NR-8).
"""

from __future__ import annotations

# Semantic version of the preprocessing *contract and semantics*.
# Bump MAJOR on any change that can alter transform outputs for the same input.
PREPROCESSING_VERSION: str = "preprocessing@1.0.0"

# Human-readable description of what this version guarantees.
PREPROCESSING_SPEC: str = (
    "Deterministic per-window EEG conditioning: linear detrend (per channel), "
    "moving-average high-pass, moving-average smoothing low-pass, and per-channel "
    "robust z-score normalization. No randomness, no wall-clock, no global state."
)


def preprocessing_version() -> str:
    """Return the canonical preprocessing version string."""
    return PREPROCESSING_VERSION
