"""Test suite for chbmit_inference module."""

from __future__ import annotations

import os
import pathlib
import pytest
import numpy as np

from backend.application_platform.chbmit_inference import CHBMitInferenceEngine

REPO = pathlib.Path(__file__).resolve().parents[1]


def test_inference_engine_on_serialized_model():
    model_path = os.path.join(str(REPO), "data", "chbmit_model.json")
    if not os.path.exists(model_path):
        pytest.skip("data/chbmit_model.json does not exist yet")
        
    engine = CHBMitInferenceEngine(model_path)
    assert engine.architecture_summary == "hybrid_eeg"
    assert "accuracy" in engine.metrics
    assert engine.model is not None
    
    # Run prediction on a dummy feature row
    dummy_features = np.random.randn(2, 11)  # 11 features
    proba = engine.predict_proba(dummy_features)
    assert proba.shape == (2, 2)
    assert np.allclose(proba.sum(axis=1), 1.0)
    
    classes = engine.predict(dummy_features)
    assert classes.shape == (2,)
    assert set(classes) <= {0, 1}
    
    # Run prediction on a raw window
    dummy_raw_window = np.random.randn(23, 1024)  # 23 channels, 1024 samples (4 seconds at 256Hz)
    pred_class, pred_proba = engine.predict_raw_window(dummy_raw_window, 256.0)
    assert pred_class in {0, 1}
    assert pred_proba.shape == (2,)
    assert np.allclose(pred_proba.sum(), 1.0)
