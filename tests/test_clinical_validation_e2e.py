"""End-to-end test for DRP-6 — Clinical Validation & Evidence Platform.

Demonstrates the full required deliverable: benchmark models -> evaluate performance ->
measure reliability -> measure calibration -> generate evidence -> track validation lineage
-> score validation readiness — over the real DRP-1 datasets / DRP-2 models on one shared
lineage tracker (no replacement systems).
"""

from __future__ import annotations

from backend.clinical_validation import ClinicalValidationService, ValidationStatus, ReadinessClass
from backend.production_models import PRODUCTION_ARCHITECTURES

from _drp6_helpers import build_feature_cohort


def test_full_clinical_validation_deliverable(eeg_fixtures, tmp_path):
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    cv = ClinicalValidationService(lineage_tracker=tracker)
    run = cv.run_validation(feats)

    assert len(run.models) == len(PRODUCTION_ARCHITECTURES)
    for o in run.models.values():
        assert o.record.status == ValidationStatus.VALIDATED
        assert o.readiness.classification == ReadinessClass.READY
        assert cv.integrity(o.record).ok
        assert tracker.verify_chain(o.record.lineage_id)
        # benchmark + reliability + calibration + evidence all present (the readiness criteria)
        assert o.benchmark and o.reliability and o.calibration and o.evidence

    # objective comparison recommends a model
    assert run.comparison.recommended_model in {o.record.model_id for o in run.models.values()}

    # all ten reports for a representative model
    rep = next(iter(run.models.values())).record
    assert len(cv.reports(rep)) == 10

    # the evidence registry holds every evidence artifact, orphan-free
    counts = cv.registry.counts()
    assert counts["validation"] == len(PRODUCTION_ARCHITECTURES)
    assert counts["benchmark"] == len(PRODUCTION_ARCHITECTURES) and counts["evidence"] == len(run.models)
    assert cv.registry.orphans() == []


def test_evidence_chain_reaches_patient(eeg_fixtures, tmp_path):
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    cv = ClinicalValidationService(lineage_tracker=tracker)
    run = cv.run_validation(feats)
    rep = next(iter(run.models.values())).record
    kinds = {n.kind for n in tracker.chain(rep.lineage_id)}
    # Dataset -> Model -> Benchmark -> Evaluation -> Evidence -> Readiness, reaching the patient
    assert {"patient", "case", "feature", "dataset", "model", "validation_benchmark",
            "validation_evaluation", "validation_evidence", "validation_readiness"} <= kinds


def test_honest_evidence_on_untuned_baselines(eeg_fixtures, tmp_path):
    """The evidence is real + traceable; it reflects untuned reference baselines on synthetic
    data (Gap G1) — the metrics are evidence, never a clinical-performance claim."""
    tracker, feats = build_feature_cohort(eeg_fixtures, tmp_path)
    cv = ClinicalValidationService(lineage_tracker=tracker)
    run = cv.run_validation(feats)
    for o in run.models.values():
        # every metric is present and in range (real, structured evidence)
        for k in ("accuracy", "sensitivity", "specificity", "roc_auc", "ece"):
            assert 0.0 <= float(o.benchmark.deterministic_metrics[k]) <= 1.0
