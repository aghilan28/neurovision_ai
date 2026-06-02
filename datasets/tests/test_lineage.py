"""Tests for data-layer lineage tracking."""

from __future__ import annotations

import pytest

from datasets.ingestion import ingest_edf_file
from datasets.lineage import LineageTracker
from datasets.lineage.tracker import (
    TYPE_METADATA,
    TYPE_RAW_FILE,
    TYPE_VALIDATION,
    LineageError,
    LineageRecord,
)


def test_ingestion_builds_full_chain(make_edf):
    tracker = LineageTracker()
    rec = ingest_edf_file(make_edf(edf_plus=True), tracker=tracker)
    assert rec.lineage_id == f"record:{rec.file_id}"
    assert len(tracker) == 4
    ancestor_ids = {n.artifact_id for n in tracker.ancestors(rec.lineage_id)}
    assert rec.file_id in ancestor_ids
    assert f"validation:{rec.file_id}" in ancestor_ids
    assert f"metadata:{rec.file_id}" in ancestor_ids


def test_lineage_nodes_carry_versions_and_fingerprints(make_edf):
    tracker = LineageTracker()
    rec = ingest_edf_file(make_edf(edf_plus=True), tracker=tracker)
    meta_node = tracker.get(f"metadata:{rec.file_id}")
    assert meta_node.artifact_type == TYPE_METADATA
    assert meta_node.operation_version
    assert meta_node.content_fingerprint
    raw_node = tracker.get(rec.file_id)
    assert raw_node.artifact_type == TYPE_RAW_FILE
    assert raw_node.content_fingerprint == rec.raw_file.content_sha256


def test_lineage_rejects_unknown_input():
    tracker = LineageTracker()
    bad = LineageRecord(
        artifact_id="x",
        artifact_type="t",
        operation="op",
        operation_version="1",
        inputs=(),
    )
    tracker.record(bad)
    from datasets.schemas.lineage import LineageEdge

    dependent = LineageRecord(
        artifact_id="y",
        artifact_type="t",
        operation="op",
        operation_version="1",
        inputs=(LineageEdge("missing", "t"),),
    )
    with pytest.raises(LineageError):
        tracker.record(dependent)


def test_lineage_round_trips(make_edf):
    tracker = LineageTracker()
    ingest_edf_file(make_edf(edf_plus=True), tracker=tracker)
    restored = LineageTracker.from_dict(tracker.to_dict())
    assert restored.to_dict() == tracker.to_dict()


def test_lineage_supports_future_downstream_node(make_edf):
    """A future preprocessing artifact can attach to the record without rewrites."""
    from datasets.schemas.lineage import LineageEdge

    tracker = LineageTracker()
    rec = ingest_edf_file(make_edf(edf_plus=True), tracker=tracker)
    downstream = LineageRecord(
        artifact_id=f"preprocessed:{rec.file_id}",
        artifact_type="preprocessing_artifact",
        operation="preprocessing.pipeline.run",
        operation_version="1.0.0",
        inputs=(LineageEdge(rec.lineage_id, TYPE_VALIDATION),),
    )
    tracker.record(downstream)
    assert rec.lineage_id in {n.artifact_id for n in tracker.ancestors(downstream.artifact_id)}
