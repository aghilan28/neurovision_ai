"""Tests for DRP-6 — Clinical Validation & Evidence Platform.

Exercises benchmarking, calibration, reliability, the evidence registry, the comparison
engine, readiness, audit, lineage, reports, schemas, and boundary/missing/corrupted/invalid
conditions — using the **real** DRP-1 datasets / DRP-2 models / DRP-3 serving outputs (no
replacement systems).
"""

from __future__ import annotations

import dataclasses

import pytest

from ml.lineage import LineageTracker
from backend.clinical_validation import (
    ClinicalValidationService, ClinicalValidationError, ValidationStatus, ReadinessClass,
    ValidationReadinessEngine, EvidenceRegistry, RegistryError, build_comparison, ComparisonError,
    sensitivity_specificity, ENTITY_CONTRACTS, validate_entity,
)
from backend.production_models import PRODUCTION_ARCHITECTURES

from _drp6_helpers import build_feature_cohort


def _run(eeg_fixtures, tmp_path):
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    cv = ClinicalValidationService(lineage_tracker=tracker)
    return tracker, feats, cv, cv.run_validation(feats)


# =============================================================================
# Benchmarking (DRP6-C)
# =============================================================================
def test_sensitivity_specificity_from_confusion():
    # 2-class perfect confusion -> sensitivity = specificity = 1.0
    sens, spec = sensitivity_specificity(((5, 0), (0, 5)))
    assert sens == pytest.approx(1.0) and spec == pytest.approx(1.0)
    # all-wrong -> 0.0
    s2, sp2 = sensitivity_specificity(((0, 5), (5, 0)))
    assert s2 == pytest.approx(0.0) and sp2 == pytest.approx(0.0)


def test_benchmark_has_clinical_metric_set(eeg_fixtures, tmp_path):
    _, _, cv, run = _run(eeg_fixtures, tmp_path)
    bm = next(iter(run.models.values())).benchmark
    required = {"accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "sensitivity",
                "specificity", "ece", "brier"}
    assert required <= set(bm.deterministic_metrics)
    assert {"latency_ms_per_sample", "inference_time_ms"} <= set(bm.performance)


# =============================================================================
# End-to-end validation run + registry/audit/lineage (DRP6-G/H)
# =============================================================================
def test_validation_run_all_architectures(eeg_fixtures, tmp_path):
    tracker, feats, cv, run = _run(eeg_fixtures, tmp_path)
    assert set(run.models) == {a.value for a in PRODUCTION_ARCHITECTURES}
    for o in run.models.values():
        r = o.record
        assert r.status == ValidationStatus.VALIDATED
        assert o.readiness.classification == ReadinessClass.READY
        # evidence registry: registered + orphan-free
        assert cv.registry.exists(r.validation_id) and cv.registry.orphans() == []
        # audit: verified + head match
        log = cv.audit_log_for(r.validation_id)
        assert log.verify() and r.audit_head == log.head
        # lineage: the full evidence chain reaches the patient
        assert tracker.verify_chain(r.lineage_id)
        kinds = {n.kind for n in tracker.chain(r.lineage_id)}
        assert {"patient", "dataset", "model", "validation_benchmark", "validation_evaluation",
                "validation_evidence", "validation_readiness"} <= kinds
        # integrity
        assert cv.integrity(r).ok, [c.name for c in cv.integrity(r).failures()]
        # immutability
        with pytest.raises(dataclasses.FrozenInstanceError):
            r.status = ValidationStatus.QUARANTINED


def test_reliability_repeatable_and_scored(eeg_fixtures, tmp_path):
    _, _, cv, run = _run(eeg_fixtures, tmp_path)
    for o in run.models.values():
        rel = o.reliability
        assert rel.repeatable and rel.reproducible           # deterministic platform
        assert 0.0 <= rel.reliability_score <= 1.0 and len(rel.failure_modes) >= 2
        assert all(f["handled"] for f in rel.failure_modes)  # bad inputs handled gracefully


# =============================================================================
# Comparison engine (DRP6-F)
# =============================================================================
def test_comparison_recommends_a_model(eeg_fixtures, tmp_path):
    _, _, cv, run = _run(eeg_fixtures, tmp_path)
    comparison = run.comparison
    assert comparison.n_models == 5
    assert comparison.recommended_model in {o.record.model_id for o in run.models.values()}
    assert {"accuracy", "f1", "roc_auc", "sensitivity", "specificity"} <= set(comparison.metrics)


def test_comparison_requires_two():
    with pytest.raises(ComparisonError):
        build_comparison([])


# =============================================================================
# Readiness engine (DRP6-I)
# =============================================================================
def test_readiness_requires_all_evidence():
    eng = ValidationReadinessEngine()
    tid = "validation_evidence+" + "a" * 16
    ready = eng.assess(target_id=tid, benchmark_ok=True, reliability_ok=True, calibration_ok=True,
                       evidence_ok=True, registered=True, audited=True, traceable=True)
    assert ready.classification == ReadinessClass.READY and ready.score == pytest.approx(1.0)
    no_rel = eng.assess(target_id=tid, benchmark_ok=True, reliability_ok=False, calibration_ok=True,
                        evidence_ok=True, registered=True, audited=True, traceable=True)
    assert no_rel.classification != ReadinessClass.READY
    assert "reliability_readiness" in no_rel.findings


# =============================================================================
# Evidence registry orphan guard (DRP6-G)
# =============================================================================
def test_registry_rejects_orphan_validation():
    from backend.clinical_validation.models.domain import ValidationRegistryRecord
    reg = EvidenceRegistry()
    rec = ValidationRegistryRecord(
        validation_id="clinical_validation+" + "0" * 16, model_id="model+" + "0" * 16,
        architecture="eegnet", dataset_label="primary", benchmark_id="validation_benchmark+" + "0" * 16,
        evidence_id="validation_evidence+" + "0" * 16, readiness_id="validation_readiness+" + "0" * 16,
        status=ValidationStatus.VALIDATED, readiness_class=ReadinessClass.READY, version="v",
        owner="o", creation_date="t", audit_state="", lineage_id="", dependencies=())
    with pytest.raises(RegistryError):
        reg.register_validation(rec)


# =============================================================================
# Reports (DRP6-J) + schemas (DRP6-K)
# =============================================================================
def test_reports_generate(eeg_fixtures, tmp_path):
    _, _, cv, run = _run(eeg_fixtures, tmp_path)
    rep = next(iter(run.models.values())).record
    reports = cv.reports(rep)
    expected = {"benchmark_report", "performance_report", "calibration_report", "reliability_report",
                "comparison_report", "evidence_report", "readiness_report", "audit_report",
                "lineage_report", "clinical_validation_summary"}
    assert expected == set(reports)
    assert reports["clinical_validation_summary"]["ok"]


def test_entity_contracts_cover_records():
    for name in ("BenchmarkRecord", "PerformanceRecord", "ReliabilityRecord", "CalibrationRecord",
                 "ComparisonRecord", "EvidenceRecord", "ReadinessRecord", "ClinicalValidationRecord"):
        assert name in ENTITY_CONTRACTS
    ok, missing = validate_entity("BenchmarkRecord", {
        "benchmark_id": "b", "model_id": "m", "architecture": "eegnet", "dataset_label": "primary",
        "deterministic_metrics": {"accuracy": 1.0}, "performance": {}, "source_benchmark_id": "s"})
    assert ok and missing == []


# =============================================================================
# Cross-run determinism (NR-9/NR-10)
# =============================================================================
def test_cross_run_determinism(eeg_fixtures, tmp_path):
    # Run validation twice over the SAME feature cohort, so the underlying (content-addressed)
    # models are identical -- this isolates the clinical-validation layer's own determinism.
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    a = ClinicalValidationService(lineage_tracker=tracker).run_validation(feats).models["eegnet"].record
    b = ClinicalValidationService(lineage_tracker=tracker).run_validation(feats).models["eegnet"].record
    assert a.validation_id == b.validation_id
    assert a.version.version == b.version.version
    assert a.benchmark_id == b.benchmark_id and a.evidence_id == b.evidence_id


# =============================================================================
# Invalid input
# =============================================================================
def test_empty_features_raises():
    cv = ClinicalValidationService(lineage_tracker=LineageTracker())
    with pytest.raises(ClinicalValidationError):
        cv.run_validation([])
