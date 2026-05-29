"""Tests for the uncertainty & calibration layer (V1-P6)."""

from __future__ import annotations

import numpy as np
import pytest

from ml.uncertainty import (
    CalibrationPipeline, TemperatureScaler, SplitConformalPredictor, CoverageTracker,
    RiskAssessor, ReliabilityAnalyzer, UncertaintyPipeline, UncertaintyValidator,
    UncertaintyRegistry, UncertaintyRecord,
)
from ml.uncertainty._math import softmax, negative_log_likelihood, conformal_quantile


# --- calibration --------------------------------------------------------------
def test_temperature_scaling_reduces_nll():
    rng = np.random.default_rng(0)
    logits = rng.normal(size=(300, 4)) * 4.0  # overconfident logits
    labels = logits.argmax(axis=1)
    # flip some labels to create miscalibration
    flip = rng.choice(300, size=60, replace=False)
    labels[flip] = (labels[flip] + 1) % 4
    scaler = TemperatureScaler().fit(logits, labels)
    nll_before = negative_log_likelihood(softmax(logits), labels)
    nll_after = negative_log_likelihood(scaler.transform(logits), labels)
    assert nll_after <= nll_before + 1e-9
    assert scaler.temperature > 0


def test_calibration_pipeline_outputs(trained_for_uncertainty):
    d = trained_for_uncertainty
    result, scaler = CalibrationPipeline().calibrate(d["calib_logits"], d["calib_labels"])
    assert result.temperature > 0
    assert result.calibration_version.startswith("calibration@")
    # post-fit ECE on the fit set should not be worse than pre (it minimizes NLL,
    # but on the fit set ECE typically does not increase materially)
    assert result.post_ece <= result.pre_ece + 0.05
    probs = scaler.transform(d["calib_logits"])
    assert np.allclose(probs.sum(axis=1), 1.0)


# --- conformal ----------------------------------------------------------------
def test_conformal_quantile_level():
    scores = np.linspace(0, 1, 100)
    q = conformal_quantile(scores, alpha=0.1)
    assert 0.0 <= q <= 1.0


def test_split_conformal_meets_coverage(trained_for_uncertainty):
    d = trained_for_uncertainty
    scaler = TemperatureScaler().fit(d["calib_logits"], d["calib_labels"])
    calib_probs = scaler.transform(d["calib_logits"])
    test_probs = scaler.transform(d["test_logits"])
    cp = SplitConformalPredictor(alpha=0.1).fit(calib_probs, d["calib_labels"])
    result = cp.predict(test_probs, d["class_names"])
    # empirical coverage on test should be near/above target (allow finite-sample slack)
    y = d["test_labels"]
    covered = result.prediction_sets[np.arange(len(y)), y].mean()
    assert covered >= result.target_coverage - 0.1
    # force_nonempty => no empty sets
    assert int((result.set_sizes() == 0).sum()) == 0


def test_conformal_alpha_validation():
    with pytest.raises(ValueError):
        SplitConformalPredictor(alpha=1.5)


# --- coverage -----------------------------------------------------------------
def test_coverage_tracker_counts_violations(dataset):
    k = dataset.n_classes
    n = 40
    rng = np.random.default_rng(2)
    labels = rng.integers(0, k, size=n)
    sets = np.zeros((n, k), dtype=bool)
    sets[np.arange(n), labels] = True  # perfect coverage
    # break coverage for the first 5: clear true class, set a wrong class (row-wise)
    sets[np.arange(5), labels[:5]] = False
    sets[np.arange(5), (labels[:5] + 1) % k] = True
    res = CoverageTracker().assess(prediction_sets=sets, labels=labels, target_coverage=0.9,
                                   class_names=dataset.class_names)
    assert res.n_violations == 5
    assert abs(res.observed_coverage - (n - 5) / n) < 1e-9


# --- risk ---------------------------------------------------------------------
def test_risk_abstains_on_ambiguous_sets(dataset):
    k = dataset.n_classes
    probs = np.full((3, k), 1.0 / k)  # maximally uncertain
    probs[0] = 0.0; probs[0, 0] = 1.0  # confident singleton for row 0
    probs = probs / probs.sum(axis=1, keepdims=True)
    sets = np.ones((3, k), dtype=bool)  # ambiguous full sets
    sets[0] = False; sets[0, 0] = True  # singleton for row 0
    res = RiskAssessor().assess(calibrated_probs=probs, class_names=dataset.class_names,
                                prediction_sets=sets)
    assert res.abstain[1] and res.abstain[2]   # ambiguous => abstain
    assert not res.abstain[0]                   # confident singleton => keep
    assert 0.0 <= res.abstain_rate <= 1.0
    assert res.risk_scores.shape == (3,)


# --- reliability --------------------------------------------------------------
def test_reliability_artifacts_structure(trained_for_uncertainty):
    d = trained_for_uncertainty
    scaler = TemperatureScaler().fit(d["calib_logits"], d["calib_labels"])
    probs = scaler.transform(d["test_logits"])
    art = ReliabilityAnalyzer().analyze(calibrated_probs=probs, labels=d["test_labels"],
                                        class_names=d["class_names"])
    out = art.to_dict()
    assert out["reliability_diagram"] and out["calibration_table"]
    assert "counts" in out["confidence_histogram"]
    assert set(out["prediction_confidence_profiles"]).issubset(set(d["class_names"]))


# --- full uncertainty pipeline ------------------------------------------------
def test_uncertainty_pipeline_end_to_end_and_deterministic(trained_for_uncertainty):
    d = trained_for_uncertainty
    up = UncertaintyPipeline(alpha=0.1)
    out1 = up.run(calib_logits=d["calib_logits"], calib_labels=d["calib_labels"],
                  eval_logits=d["test_logits"], eval_labels=d["test_labels"], class_names=d["class_names"])
    out2 = up.run(calib_logits=d["calib_logits"], calib_labels=d["calib_labels"],
                  eval_logits=d["test_logits"], eval_labels=d["test_labels"], class_names=d["class_names"])
    assert out1.temperature == out2.temperature
    assert np.allclose(out1.calibrated_test_probs, out2.calibrated_test_probs)
    assert out1.coverage.observed_coverage >= out1.conformal.target_coverage - 0.1


def test_uncertainty_validation_passes(trained_for_uncertainty, split):
    d = trained_for_uncertainty
    out = UncertaintyPipeline(alpha=0.1).run(
        calib_logits=d["calib_logits"], calib_labels=d["calib_labels"],
        eval_logits=d["test_logits"], eval_labels=d["test_labels"], class_names=d["class_names"])
    report = UncertaintyValidator().validate(
        calibration=out.calibration, conformal=out.conformal, coverage=out.coverage,
        calibration_patients=split.calibration_patients, test_patients=split.test_patients,
        clinically_complete=True)
    assert report.ok is True
    names = {c.name for c in report.checks}
    assert {"calibration_measured", "conformal_assessed", "calibration_patient_disjoint",
            "coverage_reliable", "clinical_completeness"}.issubset(names)


def test_uncertainty_registry_rejects_conflicting_records():
    reg = UncertaintyRegistry()
    rec = UncertaintyRecord(uncertainty_id="uncertainty+1", model_version="m@1",
                            dataset_version="ds@1", lineage_id="lineage+1", temperature=1.0)
    reg.register(rec)
    reg.register(rec)  # idempotent
    conflict = UncertaintyRecord(uncertainty_id="uncertainty+1", model_version="m@1",
                                 dataset_version="ds@1", lineage_id="lineage+1", temperature=2.0)
    with pytest.raises(ValueError):
        reg.register(conflict)
