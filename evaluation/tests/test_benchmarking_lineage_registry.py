"""Tests for benchmarking provenance, evaluation lineage, and the registry."""

from __future__ import annotations

import numpy as np
import pytest

from evaluation._provenance import VersionBundle
from evaluation.benchmarking import BenchmarkProvenanceError, build_benchmark_record
from evaluation.lineage import build_evaluation_lineage
from evaluation.metrics import default_metric_registry
from evaluation.registry import EvaluationRegistry, RegisteredEvaluation


def _metric_results():
    reg = default_metric_registry()
    yt = np.array([0, 1, 1, 0])
    yp = np.array([0, 1, 0, 0])
    return {"accuracy": reg.compute("accuracy", y_true=yt, y_pred=yp)}


def _full_versions():
    return VersionBundle(
        evaluation_version="1.0.0", dataset_id="ds", dataset_version="v1",
        split_id="split-abc", split_generator_version="1.0.0",
        preprocessing_version="1.0.0", metrics_version="1.0.0",
    )


def test_benchmark_requires_provenance():
    results = _metric_results()
    incomplete = VersionBundle(evaluation_version="1.0.0", dataset_id="ds")  # missing required
    with pytest.raises(BenchmarkProvenanceError):
        build_benchmark_record(incomplete, results, split_fingerprint="fp")


def test_benchmark_built_with_full_provenance():
    record = build_benchmark_record(_full_versions(), _metric_results(), split_fingerprint="fp")
    assert record.benchmark_id.startswith("bench-")
    assert record.versions.dataset_version == "v1"
    assert "accuracy" in record.metrics


def test_benchmark_fingerprint_timestamp_independent():
    a = build_benchmark_record(_full_versions(), _metric_results(), split_fingerprint="fp", created_at="t1")
    b = build_benchmark_record(_full_versions(), _metric_results(), split_fingerprint="fp", created_at="t2")
    assert a.content_fingerprint == b.content_fingerprint


def test_lineage_completeness():
    complete = build_evaluation_lineage(
        _full_versions(), split_population_fingerprint="pf", split_fingerprint="sf",
        metric_results=_metric_results(),
    )
    assert complete.is_complete()
    incomplete = build_evaluation_lineage(
        VersionBundle(evaluation_version="1.0.0"), split_population_fingerprint="pf",
        split_fingerprint="sf", metric_results=_metric_results(),
    )
    assert not incomplete.is_complete()


def test_lineage_records_metric_fingerprints():
    results = _metric_results()
    lineage = build_evaluation_lineage(
        _full_versions(), split_population_fingerprint="pf", split_fingerprint="sf",
        metric_results=results,
    )
    assert lineage.metric_fingerprints["accuracy"] == results["accuracy"].inputs_fingerprint


def test_registry_register_find_and_persist(tmp_path):
    reg = EvaluationRegistry()
    entry = RegisteredEvaluation(
        run_id="eval-1", evaluation_version="1.0.0", versions=_full_versions(),
        split_id="split-abc", metric_names=("accuracy",), result_fingerprint="rf",
        approved=True,
    )
    reg.register(entry)
    assert "eval-1" in reg
    assert len(reg.find_by_dataset("ds")) == 1
    assert len(reg.find_by_split("split-abc")) == 1

    p = tmp_path / "eval_registry.json"
    reg.save(p)
    first = p.read_bytes()
    EvaluationRegistry.load(p).save(p)
    assert p.read_bytes() == first  # deterministic persistence
    assert EvaluationRegistry.load(p).get("eval-1").approved is True
