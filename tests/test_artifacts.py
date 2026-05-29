"""Tests for artifact tracking: deterministic serialization, checksums, integrity."""

from __future__ import annotations

import numpy as np
import pytest

from ml.artifacts import ArtifactStore, serialize_weights, deserialize_weights
from ml.artifacts.store import IntegrityError


def test_weights_serialization_is_deterministic_and_roundtrips():
    w = {"head::W": np.arange(12, dtype=np.float64).reshape(3, 4), "extractor::k": np.ones((2, 2), np.float32)}
    blob1 = serialize_weights(w)
    blob2 = serialize_weights(w)
    assert blob1 == blob2  # byte-identical (no timestamps, unlike np.savez)
    back = deserialize_weights(blob1)
    assert set(back) == set(w)
    for k in w:
        assert np.array_equal(back[k], w[k])


def test_save_and_load_weights_with_checksum(tmp_path):
    store = ArtifactStore(str(tmp_path))
    w = {"head::W": np.arange(6, dtype=np.float64).reshape(2, 3)}
    ref = store.save_weights("m/v1/weights", w)
    assert ref.checksum and ref.kind == "weights"
    loaded = store.load_weights(ref)
    assert np.array_equal(loaded["head::W"], w["head::W"])
    assert store.verify(ref) is True


def test_silent_modification_is_detected(tmp_path):
    store = ArtifactStore(str(tmp_path))
    ref = store.save_weights("m/v1/weights", {"head::W": np.ones((2, 2))})
    # tamper with the file on disk
    path = store._abspath(ref.relpath)
    with open(path, "ab") as fh:
        fh.write(b"\x00corrupt")
    assert store.verify(ref) is False
    with pytest.raises(IntegrityError):
        store.load_weights(ref)


def test_json_artifacts_are_canonical_and_checksummed(tmp_path):
    store = ArtifactStore(str(tmp_path))
    ref = store.save_json("report", {"b": 2, "a": 1})
    assert store.verify(ref) is True
    loaded = store.load_json(ref)
    assert loaded == {"a": 1, "b": 2}


def test_manifest_lists_artifacts(tmp_path):
    store = ArtifactStore(str(tmp_path))
    store.save_json("a", {"x": 1})
    store.save_weights("b", {"head::W": np.zeros((1, 1))})
    manifest = store.manifest()
    assert set(manifest["artifacts"]) == {"a", "b"}
    assert store.verify() is True
