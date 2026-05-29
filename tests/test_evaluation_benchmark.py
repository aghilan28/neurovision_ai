"""Tests for the evaluation foundation + benchmarking integration (V1-P4/P5)."""

from __future__ import annotations

import numpy as np
import pytest

from evaluation import (
    PatientDisjointEvaluator, compute_metrics, expected_calibration_error,
    brier_score, empirical_coverage, verify_patient_disjoint, EVALUATION_VERSION,
)
from ml.benchmarking import EvaluationResult, EvaluationPort, BenchmarkRegistry, build_benchmark_record


def test_metrics_basic_properties(dataset):
    n, k = 50, dataset.n_classes
    rng = np.random.default_rng(0)
    labels = rng.integers(0, k, size=n)
    probs = np.eye(k)[labels]  # perfect predictions
    overall, per_class = compute_metrics(probs, labels, dataset.class_names)
    assert overall["accuracy"] == 1.0
    assert overall["macro_f1"] == 1.0
    assert set(per_class) == set(dataset.class_names)


def test_calibration_metrics_ranges():
    rng = np.random.default_rng(1)
    probs = rng.dirichlet(np.ones(3), size=200)
    labels = rng.integers(0, 3, size=200)
    ece, mce, bins = expected_calibration_error(probs, labels)
    assert 0.0 <= ece <= 1.0 and 0.0 <= mce <= 1.0
    assert 0.0 <= brier_score(probs, labels) <= 2.0


def test_verify_patient_disjoint():
    ok, overlap = verify_patient_disjoint([1, 2, 3], [4, 5])
    assert ok and overlap == []
    bad, overlap = verify_patient_disjoint([1, 2], [2, 3])
    assert not bad and overlap == [2]


def test_evaluator_implements_port():
    assert isinstance(PatientDisjointEvaluator(), EvaluationPort)


def test_evaluator_marks_patient_disjoint_only_with_train_ids(trained_model, prepared, dataset, split):
    probs = trained_model.predict_proba(prepared.x_test)
    ev = PatientDisjointEvaluator()
    # without train patients -> cannot prove disjoint -> False (NR-3 conservative)
    r0 = ev.evaluate(probabilities=probs, labels=prepared.y_test, patient_ids=prepared.p_test,
                     class_names=dataset.class_names, dataset_version=dataset.dataset_version,
                     split_version=split.split_version)
    assert r0.is_patient_disjoint() is False
    # with train patients -> proven disjoint -> True
    r1 = ev.evaluate(probabilities=probs, labels=prepared.y_test, patient_ids=prepared.p_test,
                     class_names=dataset.class_names, dataset_version=dataset.dataset_version,
                     split_version=split.split_version, train_patient_ids=split.train_patients)
    assert r1.is_patient_disjoint() is True
    assert r1.evaluation_version == EVALUATION_VERSION


def test_benchmark_refuses_non_patient_disjoint():
    ev = EvaluationResult(evaluation_version="evaluation@1.0.0", metrics={"macro_f1": 0.5},
                          per_class={}, evaluation_audit={"patient_disjoint": False})
    with pytest.raises(ValueError):
        build_benchmark_record(model_name="m", model_version="m@1", evaluation=ev,
                               dataset_version="ds@1", split_summary={"split_version": "s@1"},
                               version_bundle={}, lineage_bundle=[])


def test_benchmark_record_and_registry():
    ev = EvaluationResult(evaluation_version="evaluation@1.0.0",
                          metrics={"macro_f1": 0.8, "accuracy": 0.82}, per_class={},
                          evaluation_audit={"patient_disjoint": True})
    rec = build_benchmark_record(model_name="tcn", model_version="tcn@1+x", evaluation=ev,
                                 dataset_version="ds@1", split_summary={"split_version": "s@1"},
                                 version_bundle={"model_version": "tcn@1+x"}, lineage_bundle=[])
    reg = BenchmarkRegistry()
    reg.register(rec)
    assert rec.benchmark_id in reg.list_benchmarks()
    # benchmark id is reproducible
    rec2 = build_benchmark_record(model_name="tcn", model_version="tcn@1+x", evaluation=ev,
                                  dataset_version="ds@1", split_summary={"split_version": "s@1"},
                                  version_bundle={"model_version": "tcn@1+x"}, lineage_bundle=[])
    assert rec2.benchmark_id == rec.benchmark_id
    lb = reg.leaderboard("macro_f1")
    assert lb[0]["macro_f1"] == 0.8
