"""Lineage tracker and the ingestion-lineage builder.

The :class:`LineageTracker` is an append-only store of
:class:`~datasets.schemas.lineage.LineageRecord` nodes with acyclicity enforced on
insertion (a node may only reference inputs that already exist). It can resolve the
transitive ancestry of any artifact, which is the operational form of end-to-end
traceability.
"""

from __future__ import annotations

from typing import Any

from datasets._canonical import canonical_fingerprint
from datasets.schemas.lineage import LineageEdge, LineageRecord
from datasets.schemas.metadata_record import MetadataRecord
from datasets.schemas.raw_eeg_file import RawEegFile
from datasets.schemas.reports import ValidationReport

#: Version of the lineage-construction logic (recorded on built nodes).
LINEAGE_OPERATION_VERSION = "1.0.0"

# Stable artifact-type tokens.
TYPE_RAW_FILE = "raw_eeg_file"
TYPE_VALIDATION = "validation_report"
TYPE_METADATA = "metadata_record"
TYPE_RECORD = "validated_record"


class LineageError(ValueError):
    """Raised on an invalid lineage operation (unknown input or cycle)."""


class LineageTracker:
    """An append-only, acyclic provenance store."""

    def __init__(self) -> None:
        self._nodes: dict[str, LineageRecord] = {}

    def __contains__(self, artifact_id: object) -> bool:
        return artifact_id in self._nodes

    def __len__(self) -> int:
        return len(self._nodes)

    def record(self, node: LineageRecord, *, allow_replace: bool = False) -> LineageRecord:
        """Add ``node``; every referenced input must already be present (acyclicity).

        Re-recording an identical node id is idempotent unless ``allow_replace`` is
        set; recording a *different* node under an existing id without
        ``allow_replace`` is rejected to keep lineage immutable/auditable.
        """
        for edge in node.inputs:
            if edge.input_id not in self._nodes:
                raise LineageError(
                    f"lineage input {edge.input_id!r} for {node.artifact_id!r} does not exist"
                )
            if edge.input_id == node.artifact_id:
                raise LineageError(f"lineage node {node.artifact_id!r} cannot depend on itself")

        existing = self._nodes.get(node.artifact_id)
        if existing is not None and not allow_replace and existing != node:
            raise LineageError(
                f"lineage node {node.artifact_id!r} already exists with different content"
            )
        self._nodes[node.artifact_id] = node
        return node

    def get(self, artifact_id: str) -> LineageRecord:
        return self._nodes[artifact_id]

    def ancestors(self, artifact_id: str) -> tuple[LineageRecord, ...]:
        """Return all transitive inputs of ``artifact_id`` (deterministic order)."""
        if artifact_id not in self._nodes:
            raise LineageError(f"unknown artifact {artifact_id!r}")
        seen: set[str] = set()
        ordered: list[LineageRecord] = []
        frontier = [e.input_id for e in self._nodes[artifact_id].inputs]
        while frontier:
            current = frontier.pop(0)
            if current in seen or current not in self._nodes:
                continue
            seen.add(current)
            node = self._nodes[current]
            ordered.append(node)
            frontier.extend(e.input_id for e in node.inputs)
        return tuple(sorted(ordered, key=lambda n: n.artifact_id))

    def nodes(self) -> tuple[LineageRecord, ...]:
        return tuple(self._nodes[k] for k in sorted(self._nodes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "lineage_operation_version": LINEAGE_OPERATION_VERSION,
            "nodes": [n.to_dict() for n in self.nodes()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LineageTracker:
        tracker = cls()
        # Insert in dependency order: nodes with no inputs first, then the rest.
        raw_nodes = [LineageRecord.from_dict(n) for n in data.get("nodes", [])]
        pending = list(raw_nodes)
        guard = 0
        while pending:
            progressed = False
            still: list[LineageRecord] = []
            for node in pending:
                if all(e.input_id in tracker for e in node.inputs):
                    tracker.record(node, allow_replace=True)
                    progressed = True
                else:
                    still.append(node)
            pending = still
            guard += 1
            if not progressed:
                # Remaining nodes reference unknown inputs; record as-is is unsafe.
                raise LineageError("cannot reconstruct lineage: missing or cyclic inputs")
            if guard > len(raw_nodes) + 1:
                break
        return tracker


def build_ingestion_lineage(
    tracker: LineageTracker,
    raw_file: RawEegFile,
    validation: ValidationReport,
    metadata: MetadataRecord,
    *,
    recorded_at: str | None = None,
) -> str:
    """Record the standard ingestion provenance chain and return the record node id.

    Chain (acyclic):
        raw file -> validation report -> metadata record -> validated record
    """
    file_node_id = raw_file.file_id
    tracker.record(
        LineageRecord(
            artifact_id=file_node_id,
            artifact_type=TYPE_RAW_FILE,
            operation="ingestion.read_bytes",
            operation_version=LINEAGE_OPERATION_VERSION,
            inputs=(),
            content_fingerprint=raw_file.content_sha256,
            recorded_at=recorded_at,
            attributes={"file_name": raw_file.file_name, "format": raw_file.detected_format.value},
        ),
        allow_replace=True,
    )

    validation_id = f"validation:{raw_file.file_id}"
    tracker.record(
        LineageRecord(
            artifact_id=validation_id,
            artifact_type=TYPE_VALIDATION,
            operation="validation.run_all_checks",
            operation_version=validation.validator_version or LINEAGE_OPERATION_VERSION,
            inputs=(LineageEdge(file_node_id, TYPE_RAW_FILE),),
            content_fingerprint=canonical_fingerprint(validation.to_dict()),
            recorded_at=recorded_at,
            attributes={"status": validation.status.value},
        ),
        allow_replace=True,
    )

    metadata_id = f"metadata:{raw_file.file_id}"
    tracker.record(
        LineageRecord(
            artifact_id=metadata_id,
            artifact_type=TYPE_METADATA,
            operation="metadata.extract",
            operation_version=metadata.extractor_version or LINEAGE_OPERATION_VERSION,
            inputs=(LineageEdge(file_node_id, TYPE_RAW_FILE),),
            content_fingerprint=canonical_fingerprint(metadata.to_dict()),
            recorded_at=recorded_at,
            attributes={"patient_id": metadata.patient_id, "recording_id": metadata.recording_id},
        ),
        allow_replace=True,
    )

    record_id = f"record:{raw_file.file_id}"
    tracker.record(
        LineageRecord(
            artifact_id=record_id,
            artifact_type=TYPE_RECORD,
            operation="ingestion.ingest_edf_file",
            operation_version=LINEAGE_OPERATION_VERSION,
            inputs=(
                LineageEdge(validation_id, TYPE_VALIDATION),
                LineageEdge(metadata_id, TYPE_METADATA),
            ),
            recorded_at=recorded_at,
        ),
        allow_replace=True,
    )
    return record_id
