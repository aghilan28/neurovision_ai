"""Tests for the metrics framework (correctness against known values)."""

from __future__ import annotations

import numpy as np
import pytest

from evaluation.metrics import (
    accuracy,
    auprc,
    auroc,
    balanced_accuracy,
    confusion_matrix,
    default_metric_registry,
    f1_score,
    sensitivity_specificity,
)
from evaluation.metrics.calibration import CalibrationNotAvailable


def test_accuracy_known():
    yt = np.array([0, 0, 1, 1, 1])
    yp = np.array([0, 1, 1, 1, 0])
    assert accuracy(yt, yp) == pytest.approx(0.6)


def test_confusion_matrix_known():
    yt = np.array([0, 0, 1, 1, 1])
    yp = np.array([0, 1, 1, 1, 0])
    cm = confusion_matrix(yt, yp)
    assert cm.tolist() == [[1, 1], [1, 2]]


def test_sensitivity_specificity_known():
    yt = np.array([0, 0, 1, 1, 1])
    yp = np.array([0, 1, 1, 1, 0])
    ss = sensitivity_specificity(yt, yp)
    assert ss["sensitivity"] == pytest.approx(2 / 3)
    assert ss["specificity"] == pytest.approx(0.5)


@pytest.mark.scientific
def test_auroc_perfect_reversed_and_ties():
    yt = np.array([0, 0, 1, 1])
    ys = np.array([0.1, 0.2, 0.8, 0.9])
    assert auroc(yt, ys) == pytest.approx(1.0)
    assert auroc(yt, -ys) == pytest.approx(0.0)
    assert auroc(np.array([0, 1, 0, 1]), np.array([0.5, 0.5, 0.5, 0.5])) == pytest.approx(0.5)


@pytest.mark.scientific
def test_auprc_perfect_and_single_class():
    yt = np.array([0, 0, 1, 1])
    ys = np.array([0.1, 0.2, 0.8, 0.9])
    assert auprc(yt, ys) == pytest.approx(1.0)
    assert auroc(np.array([1, 1, 1]), np.array([0.1, 0.2, 0.3])) is None
    assert auprc(np.array([0, 0, 0]), np.array([0.1, 0.2, 0.3])) is None


def test_balanced_accuracy_and_f1_multiclass():
    yt = np.array([0, 1, 2, 2, 1, 0])
    yp = np.array([0, 2, 2, 2, 1, 0])
    assert 0.0 <= balanced_accuracy(yt, yp) <= 1.0
    assert 0.0 <= f1_score(yt, yp) <= 1.0


def test_registry_compute_and_provenance():
    reg = default_metric_registry()
    yt = np.array([0, 1, 1, 0])
    yp = np.array([0, 1, 0, 0])
    result = reg.compute("accuracy", y_true=yt, y_pred=yp)
    assert result.value == pytest.approx(0.75)
    assert result.inputs_fingerprint  # provenance present
    assert result.version


def test_registry_suite_skips_placeholders():
    reg = default_metric_registry()
    yt = np.array([0, 1, 1, 0])
    ys = np.array([0.2, 0.9, 0.7, 0.1])
    yp = (ys > 0.5).astype(int)
    suite = reg.compute_suite(
        ["accuracy", "auroc", "expected_calibration_error"],
        y_true=yt, y_pred=yp, y_score=ys,
    )
    assert "accuracy" in suite and "auroc" in suite
    assert "expected_calibration_error" not in suite  # placeholder skipped


def test_calibration_placeholder_raises_when_computed():
    reg = default_metric_registry()
    with pytest.raises(CalibrationNotAvailable):
        reg.compute("expected_calibration_error", y_true=np.array([0, 1]), y_score=np.array([0.2, 0.8]))


def test_calibration_registered_as_placeholder():
    reg = default_metric_registry()
    assert reg.get("expected_calibration_error").placeholder is True
    assert reg.get("coverage").placeholder is True
