"""Tests for the typed, versioned model I/O contracts (V1-P5)."""

from __future__ import annotations

import numpy as np
import pytest

from ml.schemas import (
    InputWindow, InputBatch, ProbabilityOutput, ClassOutput, MetadataOutput,
    UncertaintyPlaceholder, ConformalOutput, Prediction, CONTRACT_VERSION,
)


def test_probability_output_validates_rows_sum_to_one():
    ProbabilityOutput(np.array([[0.2, 0.8], [0.5, 0.5]]), ("a", "b"))
    with pytest.raises(ValueError):
        ProbabilityOutput(np.array([[0.2, 0.2]]), ("a", "b"))


def test_probability_output_confidence():
    p = ProbabilityOutput(np.array([[0.7, 0.3], [0.4, 0.6]]), ("a", "b"))
    assert np.allclose(p.confidence(), [0.7, 0.6])


def test_class_output_range_validation():
    ClassOutput(np.array([0, 1]), ("a", "b"))
    with pytest.raises(ValueError):
        ClassOutput(np.array([0, 2]), ("a", "b"))


def test_input_batch_shape_validation():
    with pytest.raises(ValueError):
        InputBatch(np.zeros((4, 8)), np.zeros(4), "preprocessing@1.0.0")  # 2-D not allowed
    b = InputBatch(np.zeros((4, 8, 16)), np.arange(4), "preprocessing@1.0.0")
    assert b.n == 4 and b.n_channels == 8 and b.n_samples == 16


def test_uncertainty_placeholder_starts_uncalibrated():
    u = UncertaintyPlaceholder()
    assert u.is_calibrated() is False


def test_conformal_output_set_sizes():
    sets = np.array([[True, False, True], [True, False, False]])
    c = ConformalOutput(sets, 0.9, ("a", "b", "c"), "conformal@1.0.0")
    assert list(c.set_sizes()) == [2, 1]


def test_prediction_clinical_completeness_gate():
    p = ProbabilityOutput(np.array([[0.7, 0.3]]), ("a", "b"))
    c = ClassOutput(np.array([0]), ("a", "b"))
    m = MetadataOutput("simple_cnn", "m@1", "simple_cnn@1.0.0", "preprocessing@1.0.0")
    pred = Prediction(p, c, m)  # default uncertainty => not calibrated
    assert pred.is_clinically_complete() is False
    calibrated = Prediction(p, c, m, uncertainty=UncertaintyPlaceholder(calibrated=True))
    assert calibrated.is_clinically_complete() is True


def test_contracts_carry_version():
    assert CONTRACT_VERSION.startswith("model-contract@")
    m = MetadataOutput("x", "y", "z", "w")
    assert m.to_dict()["contract_version"] == CONTRACT_VERSION
