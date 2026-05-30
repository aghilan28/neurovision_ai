"""``backend/eeg_foundation/metadata`` — deterministic metadata extraction (P1-D).

Normalizes the source-reported facts of a real EEG file into an ``EEGMetadata``
record (recording id, optional patient id, acquisition date, duration, sampling
frequency, channel layout/labels, annotation count/types) stored independently of
the raw signal. Deterministic: same file -> same metadata.
"""

from __future__ import annotations

from .extractor import extract_metadata, compute_recording_id

__all__ = ["extract_metadata", "compute_recording_id"]
