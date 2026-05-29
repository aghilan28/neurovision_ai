"""``datasets.lineage`` — provenance tracking for the data layer.

Maintains the directed acyclic provenance graph that makes every artifact
traceable (AP-5, NR-11): raw file -> validation report -> metadata record ->
validated record -> dataset version, and onward to *future* processing artifacts
(e.g. preprocessing outputs) which attach as new downstream nodes without any
reshaping (AP-1, no rewrites).
"""

from __future__ import annotations

from datasets.lineage.tracker import (
    LINEAGE_OPERATION_VERSION,
    LineageTracker,
    build_ingestion_lineage,
)

__all__ = [
    "LINEAGE_OPERATION_VERSION",
    "LineageTracker",
    "build_ingestion_lineage",
]
