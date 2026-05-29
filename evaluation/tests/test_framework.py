"""End-to-end tests for the evaluation orchestrator."""

from __future__ import annotations

import pytest

from evaluation.framework import run_evaluation
from evaluation.registry import EvaluationRegistry
from evaluation.reports import evaluation_report, save_report, summary_report
from evaluation.splits import patient_disjoint_split
from evaluation.splits.schemas import Partition, SplitResult, SplitSpec


def _approved_split(population):
    return patient_disjoint_split(population, base_seed=1, dataset_id="ds", dataset_version="v1")


def test_approved_run_produces_benchmark_lineage_audit(population, binary_predictions):
    split = _approved_split(population)
    run = run_evaluation(
        split, binary_predictions, dataset_id="ds", dataset_version="v1",
        preprocessing_version="1.0.0",
    )
    assert run.status == "approved"
    assert run.metric_results  # metrics computed
    assert run.benchmark is not None
    assert run.lineage is not None and run.lineage.is_complete()
    assert run.audit["ok"] is True
    assert run.run_id.startswith("eval-")


@pytest.mark.leakage
def test_leaky_split_blocks_run(binary_predictions):
    leaky = SplitResult(
        spec=SplitSpec(scheme="patient_disjoint", base_seed=0, fractions={"train": 0.5, "test": 0.5}),
        partitions=(Partition("train", ("pX",), ("pX-r0",)), Partition("test", ("pX",), ("pX-r0",))),
        population_fingerprint="fp", n_patients=1, n_records=1,
    )
    run = run_evaluation(leaky, binary_predictions, dataset_version="v1", preprocessing_version="1.0.0")
    assert run.status == "blocked"
    assert run.benchmark is None
    assert not run.metric_results  # no metrics computed when leakage exists (NR-3)
    assert run.audit["ok"] is False


@pytest.mark.determinism
def test_run_is_deterministic(population, binary_predictions):
    split = _approved_split(population)
    a = run_evaluation(split, binary_predictions, dataset_id="ds", dataset_version="v1",
                       preprocessing_version="1.0.0", created_at="t1")
    b = run_evaluation(split, binary_predictions, dataset_id="ds", dataset_version="v1",
                       preprocessing_version="1.0.0", created_at="t2")
    assert a.run_id == b.run_id
    assert a.content_fingerprint == b.content_fingerprint


def test_run_registers_in_evaluation_registry(population, binary_predictions):
    reg = EvaluationRegistry()
    split = _approved_split(population)
    run = run_evaluation(split, binary_predictions, dataset_id="ds", dataset_version="v1",
                         preprocessing_version="1.0.0", evaluation_registry=reg)
    assert run.run_id in reg
    assert reg.get(run.run_id).approved is True


def test_loso_runs_are_all_patient_disjoint(population, binary_predictions):
    from evaluation.splits import leave_one_subject_out

    for fold in leave_one_subject_out(population, base_seed=0):
        run = run_evaluation(fold, binary_predictions, dataset_id="ds", dataset_version="v1",
                             preprocessing_version="1.0.0")
        assert run.status == "approved"
        assert run.split_validation.leakage.leakage_free


def test_reports_serialize_deterministically(population, binary_predictions, tmp_path):
    split = _approved_split(population)
    run = run_evaluation(split, binary_predictions, dataset_id="ds", dataset_version="v1",
                         preprocessing_version="1.0.0", created_at="fixed")
    full = evaluation_report(run)
    summary = summary_report(run)
    assert summary["status"] == "approved"
    assert summary["leakage_free"] is True
    assert "accuracy" in summary["scalar_metrics"]

    p = tmp_path / "eval.json"
    save_report(full, p)
    first = p.read_bytes()
    save_report(full, p)
    assert p.read_bytes() == first
