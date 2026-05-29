"""Fixtures for the evaluation-foundation tests."""

from __future__ import annotations

import numpy as np
import pytest

from evaluation.framework import Predictions


@pytest.fixture
def population():
    """A 6-patient population, each with one recording."""
    return {f"p{i}": [f"p{i}-r0"] for i in range(6)}


@pytest.fixture
def multi_recording_population():
    """8 patients, some with multiple recordings (patient-level splitting required)."""
    pop = {}
    for i in range(8):
        pop[f"p{i}"] = [f"p{i}-r{j}" for j in range(1 + (i % 3))]
    return pop


@pytest.fixture
def binary_predictions():
    """Deterministic synthetic binary predictions (stand-in for a model's outputs)."""
    rng = np.random.default_rng(0)
    y_true = rng.integers(0, 2, size=40)
    y_score = np.clip(y_true * 0.6 + rng.normal(0, 0.25, size=40), 0.0, 1.0)
    y_pred = (y_score > 0.5).astype(int)
    return Predictions(y_true=y_true, y_pred=y_pred, y_score=y_score, labels=(0, 1))
