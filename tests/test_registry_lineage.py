"""Tests for the model registry and lineage tracking (V1-P5)."""

from __future__ import annotations

import pytest

from ml.registry import ModelRegistry, ModelRecord, ModelStatus
from ml.lineage import LineageTracker, VersionBundle, make_lineage_record


def _record(model_version="m@1+abc", weights_sig="w1"):
    return ModelRecord(
        model_name="tcn", model_version=model_version, architecture_version="tcn@1.0.0",
        training_version="training@1.0.0+t", dataset_version="ds@1", preprocessing_version="preprocessing@1.0.0",
        lineage_id="lineage+xyz", owner="kiro", weights_signature=weights_sig, config_signature="c1",
    )


def test_register_and_get():
    reg = ModelRegistry()
    reg.register(_record())
    assert reg.exists("m@1+abc")
    assert reg.get("m@1+abc").model_name == "tcn"
    assert reg.list_models() == ["m@1+abc"]


def test_idempotent_reregistration_same_content():
    reg = ModelRegistry()
    reg.register(_record())
    reg.register(_record())  # identical content => allowed
    assert len(reg.list_models()) == 1


def test_silent_overwrite_rejected():
    reg = ModelRegistry()
    reg.register(_record(weights_sig="w1"))
    with pytest.raises(ValueError):
        reg.register(_record(weights_sig="DIFFERENT"))  # same version, different content


def test_status_transitions():
    reg = ModelRegistry()
    reg.register(_record())
    reg.set_status("m@1+abc", ModelStatus.EVALUATED)
    reg.set_status("m@1+abc", ModelStatus.BENCHMARKED)
    reg.set_status("m@1+abc", ModelStatus.REGISTERED)
    assert reg.get("m@1+abc").status == ModelStatus.REGISTERED
    with pytest.raises(ValueError):
        reg.set_status("m@1+abc", ModelStatus.TRAINED)  # illegal backward transition


def test_attach_evaluation_and_benchmark():
    reg = ModelRegistry()
    reg.register(_record())
    reg.attach_evaluation("m@1+abc", "evaluation@1.0.0")
    reg.attach_benchmark("m@1+abc", "benchmark@1.0.0")
    rec = reg.get("m@1+abc")
    assert rec.evaluation_version == "evaluation@1.0.0"
    assert rec.benchmark_version == "benchmark@1.0.0"


def test_lineage_content_addressing_is_deterministic():
    vb = VersionBundle(dataset_version="ds@1", model_version="m@1")
    r1 = make_lineage_record("training", vb, {"a": 1}, {"b": 2})
    r2 = make_lineage_record("training", vb, {"a": 1}, {"b": 2})
    assert r1.lineage_id == r2.lineage_id


def test_lineage_chain_and_verification():
    tracker = LineageTracker()
    vb = VersionBundle(model_version="m@1")
    train = tracker.record(make_lineage_record("training", vb, {}, {"w": "x"}))
    ev = tracker.record(make_lineage_record("evaluation", vb, {}, {"m": 1}, parents=(train.lineage_id,)))
    bench = tracker.record(make_lineage_record("benchmark", vb, {}, {}, parents=(ev.lineage_id,)))
    chain = tracker.chain(bench.lineage_id)
    ids = {r.lineage_id for r in chain}
    assert {train.lineage_id, ev.lineage_id, bench.lineage_id} == ids
    assert tracker.verify_chain(bench.lineage_id) is True


def test_broken_lineage_chain_detected():
    tracker = LineageTracker()
    vb = VersionBundle(model_version="m@1")
    # record a node whose parent was never recorded
    orphan = make_lineage_record("benchmark", vb, {}, {}, parents=("lineage+missing",))
    tracker.record(orphan)
    assert tracker.verify_chain(orphan.lineage_id) is False
