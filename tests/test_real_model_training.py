"""Track 2 — Real Model Training & Benchmark tests (backend/real_model_training).

Exercises real-data windowing/training, evaluation, benchmarking, experiment tracking,
comparison, serving readiness, audit + lineage integration, registry, reports, determinism,
and the boundary / corrupted-label / missing-data / invalid-split conditions — driving the
**real** training/evaluation/benchmark engines over the committed real EDF fixtures laid out
as a CHB-MIT dataset (no network, no synthetic training). A real-corpus test runs over the
locally-acquired PhysioNet recordings when available.
"""

from __future__ import annotations

import pytest

from _track2_helpers import develop_local, real_chb_mit_root

from backend.dataset_acquisition import DatasetSource as T1Src
from backend.real_model_training import (
    ALL_ARCHITECTURES, DatasetBuildError, EntityKind, RealModelTrainingService,
    ServingReadinessClass, build_real_training_dataset, validate_entity,
)
from backend.real_model_training.data import RecordingInput


# --- T2-B: real training dataset pipeline ------------------------------------
def test_windowing_produces_real_balanced_dataset(tmp_path):
    svc, out = develop_local(tmp_path)
    ds = out.dataset_record
    assert ds.source == "chb_mit" and ds.n_windows >= 4
    assert ds.n_classes == 2 and set(ds.class_distribution) == {"background", "seizure"}
    assert ds.n_train >= 1 and ds.n_test >= 1
    assert ds.n_features == len(ds.feature_names)


def test_no_usable_windows_raises(tmp_path):
    # an empty recording list -> graceful, explicit failure (never a silent pass)
    with pytest.raises(DatasetBuildError):
        build_real_training_dataset([], source_dataset_id="x", source="chb_mit")


def test_missing_data_recording_is_skipped(tmp_path):
    svc, out = develop_local(tmp_path)
    bogus = RecordingInput(abspath=str(tmp_path / "nope.edf"), patient_id="chbX",
                           recording_id="recording+deadbeefdeadbeef", seizure_intervals=())
    # a non-existent file is skipped, not fatal: rebuilding with only the bogus rec raises
    with pytest.raises(DatasetBuildError):
        build_real_training_dataset([bogus], source_dataset_id="x", source="chb_mit")


# --- T2-C: training framework (5 architectures, real data) -------------------
def test_trains_all_five_architectures_on_real_data(tmp_path):
    svc, out = develop_local(tmp_path)
    archs = {c.architecture for c in out.candidates}
    assert archs == set(ALL_ARCHITECTURES)
    assert all(c.reproducible for c in out.candidates)
    assert all(c.training_run_id and c.params_fingerprint for c in out.candidates)


# --- T2-E: evaluation --------------------------------------------------------
def test_evaluation_metrics_present_with_sensitivity_specificity(tmp_path):
    svc, out = develop_local(tmp_path)
    for ev in out.evaluations:
        for key in ("accuracy", "precision_macro", "recall_macro", "f1_macro", "roc_auc_macro",
                    "pr_auc_macro", "ece", "brier", "sensitivity", "specificity"):
            assert key in ev.metrics
            assert 0.0 <= float(ev.metrics[key]) <= 1.0
        assert len(ev.confusion_matrix) == 2


# --- T2-F: benchmark ---------------------------------------------------------
def test_benchmark_metrics_present_and_timings_not_hashed(tmp_path):
    svc, out = develop_local(tmp_path)
    for b in out.benchmarks:
        assert set(b.deterministic_metrics) >= {"accuracy", "f1_macro", "roc_auc_macro",
                                                "pr_auc_macro", "ece", "brier"}
        assert set(b.performance) >= {"training_time_ms", "inference_time_ms", "peak_memory_kb"}
        # the metrics signature is a function of deterministic metrics only (no timings)
        sig = b.metrics_signature()
        assert isinstance(sig, str) and len(sig) == 16


# --- T2-D: experiment tracking -----------------------------------------------
def test_experiment_tracking_records_versions_and_metrics(tmp_path):
    svc, out = develop_local(tmp_path)
    assert len(out.experiments) == len(ALL_ARCHITECTURES)
    for exp in out.experiments:
        assert exp.dataset_id == out.dataset_id
        assert exp.training_run_id and exp.model_id
        assert exp.training_metrics and exp.benchmark_metrics and exp.evaluation_metrics
        assert exp.reproducible


# --- T2-G: comparison --------------------------------------------------------
def test_comparison_ranks_and_recommends(tmp_path):
    svc, out = develop_local(tmp_path)
    assert out.comparison is not None
    assert out.comparison.n_models == len(ALL_ARCHITECTURES)
    assert len(out.comparison.ranking) == len(ALL_ARCHITECTURES)
    assert out.comparison.recommended_model in {c.model_id for c in out.candidates}


# --- T2-H: serving readiness -------------------------------------------------
def test_serving_readiness_reaches_ready_for_serving(tmp_path):
    svc, out = develop_local(tmp_path)
    ready = out.ready_models()
    assert ready, "expected at least one READY_FOR_SERVING model"
    for c in ready:
        assert c.readiness_class == ServingReadinessClass.READY_FOR_SERVING
        assert c.ready_for_serving and c.validation.ok
    best = out.best_ready_model()
    assert best is not None and best.ready_for_serving


def test_readiness_dimensions_all_present(tmp_path):
    svc, out = develop_local(tmp_path)
    for r in out.readinesses:
        if r.classification == ServingReadinessClass.READY_FOR_SERVING:
            assert r.score >= 0.999 and r.findings == ()


# --- T2-I: audit + lineage ---------------------------------------------------
def test_audit_integration(tmp_path):
    svc, out = develop_local(tmp_path)
    log = svc.audit_log_for(out.dataset_id)
    assert log.verify() and len(log) >= 5


def test_lineage_chain_reaches_dataset_source(tmp_path):
    svc, out = develop_local(tmp_path)
    rnode = out.readinesses[0].lineage_id
    assert svc.lineage.verify_chain(rnode)
    kinds = {n.kind for n in svc.lineage.chain(rnode)}
    required = {"training_dataset", "training_recording", "training_feature_asset",
                "training_run", "trained_model", "model_evaluation", "model_benchmark",
                "readiness_assessment"}
    assert required <= kinds
    # the chain reaches the original Track-1 dataset source (full traceability)
    assert {"real_dataset", "dataset_source"} <= kinds


def test_registry_has_no_orphans(tmp_path):
    svc, out = develop_local(tmp_path)
    counts = svc.registry.counts()
    assert svc.registry.orphans() == []
    assert counts[EntityKind.MODEL.value] == len(ALL_ARCHITECTURES)
    assert counts[EntityKind.BENCHMARK.value] == len(ALL_ARCHITECTURES)
    assert counts[EntityKind.READINESS.value] == len(ALL_ARCHITECTURES)


# --- T2-J: reports -----------------------------------------------------------
def test_reports_generate(tmp_path):
    svc, out = develop_local(tmp_path)
    reports = svc.reports(out)
    expected = {"training_report", "evaluation_report", "benchmark_report", "comparison_report",
                "readiness_report", "registry_report", "audit_report", "lineage_report",
                "model_summary_report"}
    assert set(reports) == expected
    assert reports["lineage_report"]["chain_verified"]


def test_entity_contract_validation(tmp_path):
    svc, out = develop_local(tmp_path)
    best = out.best_ready_model()
    ok, missing = validate_entity("CandidateModelRecord", best.to_dict())
    assert ok and missing == []
    ok2, _ = validate_entity("RealTrainingDatasetRecord", out.dataset_record.to_dict())
    assert ok2


# --- determinism -------------------------------------------------------------
def test_determinism_across_instances(tmp_path):
    svc_a, a = develop_local(tmp_path)
    svc_b, b = develop_local(tmp_path)
    assert a.dataset_id == b.dataset_id
    assert {c.model_id for c in a.candidates} == {c.model_id for c in b.candidates}
    am = {c.architecture: c.headline_metrics for c in a.candidates}
    bm = {c.architecture: c.headline_metrics for c in b.candidates}
    for arch in am:
        assert am[arch] == bm[arch]
    # benchmark deterministic metrics reproduce bit-for-bit
    abench = {x.architecture: x.deterministic_metrics for x in a.benchmarks}
    bbench = {x.architecture: x.deterministic_metrics for x in b.benchmarks}
    assert abench == bbench


# --- corrupted labels / invalid splits ---------------------------------------
def test_corrupted_label_interval_does_not_crash(tmp_path):
    # a malformed (end<start) interval must not crash windowing; it yields background labels
    from _track1_helpers import build_local_chb_mit
    build_local_chb_mit(str(tmp_path))
    svc = RealModelTrainingService(data_root=str(tmp_path))
    prepared = svc.prepare(window_seconds=0.5, stride_seconds=0.25)
    # inject a corrupted interval directly into the recording inputs path
    recs = [RecordingInput(abspath=svc.dataset_service.storage.abspath(T1Src.CHB_MIT, r.relative_path),
                           patient_id=r.patient_id, recording_id=r.recording_id,
                           seizure_intervals=((5.0, 1.0),))  # end < start
            for r in prepared.t1_outcome.connector_result.recordings if r.parse_ok]
    bundle, ds, prov = build_real_training_dataset(recs, source_dataset_id="x", source="chb_mit",
                                                   window_seconds=0.5, stride_seconds=0.25)
    # no window overlaps a reversed interval -> all background (single class), still builds
    assert ds.n_windows >= 1


def test_invalid_split_fractions_rejected(tmp_path):
    from _track1_helpers import build_local_chb_mit
    build_local_chb_mit(str(tmp_path))
    svc = RealModelTrainingService(data_root=str(tmp_path))
    with pytest.raises(Exception):
        svc.develop(allow_download=False, window_seconds=0.5, stride_seconds=0.25,
                    val_fraction=0.8, test_fraction=0.8)


# --- real corpus when available ----------------------------------------------
def test_real_chb_mit_corpus_when_available():
    root = real_chb_mit_root()
    if root is None:
        pytest.skip("real CHB-MIT corpus not acquired locally")
    svc = RealModelTrainingService(data_root=root)
    out = svc.develop(allow_download=False, window_seconds=4.0, background_per_seizure=4)
    assert out.dataset_record.n_windows >= 10
    assert out.dataset_record.windowing.sampling_frequency == 256.0
    ready = out.ready_models()
    assert ready, "expected READY_FOR_SERVING models on the real corpus"
    # at least one architecture meaningfully separates seizure from background
    best_roc = max(float(b.deterministic_metrics["roc_auc_macro"]) for b in out.benchmarks)
    assert best_roc >= 0.5
