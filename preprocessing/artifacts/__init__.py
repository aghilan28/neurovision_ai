"""``preprocessing.artifacts`` — output persistence + artifact reporting.

Turns a :class:`~preprocessing.pipelines.result.PreprocessingResult` into durable,
reproducible artifacts: the window/signal array (``.npz``) and a canonical-JSON
sidecar (``manifest.json``) carrying the full lineage, stage results, quality, and
fingerprints. The sidecar is content-addressable and diff-friendly so a stored
artifact can be audited and reproduced (AP-6/NR-10/NR-11).
"""

from __future__ import annotations

from preprocessing.artifacts.writer import (
    ARTIFACT_OP_VERSION,
    ArtifactReport,
    build_artifact_report,
    write_artifacts,
)

__all__ = [
    "ARTIFACT_OP_VERSION",
    "ArtifactReport",
    "build_artifact_report",
    "write_artifacts",
]
