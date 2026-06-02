"""Tests for the baseline models (V1-P5): EEGNet, TCN, SimpleCNN.

Asserts the three required architectures work, are deterministic, expose their
contracts, and round-trip their weights.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.models import build_model, available_models, ModelConfig
from ml.models.factory import ARCHITECTURE_REGISTRY


@pytest.fixture
def cfg_for(dataset):
    def _make(name):
        return ModelConfig(name=name, n_channels=dataset.n_channels,
                           n_samples=dataset.n_samples, n_classes=dataset.n_classes, seed=7)
    return _make


def test_all_three_architectures_available():
    assert set(available_models()) == {"simple_cnn", "eegnet", "tcn"}


@pytest.mark.parametrize("name", ["simple_cnn", "eegnet", "tcn"])
def test_model_trains_and_predicts(name, cfg_for, prepared):
    model = build_model(cfg_for(name))
    history = model.fit(prepared.x_train, prepared.y_train, steps=80)
    probs = model.predict_proba(prepared.x_test)
    assert probs.shape == (prepared.x_test.shape[0], len(prepared.class_names))
    assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-5)
    assert 0.0 <= history.final_train_accuracy <= 1.0
    # learns above chance on a learnable synthetic task
    test_acc = float(np.mean(model.predict(prepared.x_test) == prepared.y_test))
    assert test_acc > 0.5


@pytest.mark.parametrize("name", ["simple_cnn", "eegnet", "tcn"])
def test_model_training_is_deterministic(name, cfg_for, prepared):
    m1 = build_model(cfg_for(name)); m1.fit(prepared.x_train, prepared.y_train, steps=80)
    m2 = build_model(cfg_for(name)); m2.fit(prepared.x_train, prepared.y_train, steps=80)
    assert np.allclose(m1.predict_proba(prepared.x_test), m2.predict_proba(prepared.x_test))
    assert m1.weights_signature() == m2.weights_signature()


@pytest.mark.parametrize("name", ["simple_cnn", "eegnet", "tcn"])
def test_architecture_spec_has_contracts(name, cfg_for):
    spec = build_model(cfg_for(name)).architecture_spec()
    assert spec["name"] == name
    assert spec["architecture_version"].split("@")[0] == name
    assert spec["architecture_version"] == ARCHITECTURE_REGISTRY[name](cfg_for(name)).architecture_version
    assert "input_contract" in spec and "output_contract" in spec
    assert spec["layers"]  # non-empty layer description
    assert "config_schema" in spec


@pytest.mark.parametrize("name", ["simple_cnn", "eegnet", "tcn"])
def test_weights_roundtrip(name, cfg_for, prepared):
    m = build_model(cfg_for(name)); m.fit(prepared.x_train, prepared.y_train, steps=40)
    weights = m.get_weights()
    clone = build_model(cfg_for(name)); clone.load_weights(weights)
    assert np.allclose(m.predict_proba(prepared.x_test), clone.predict_proba(prepared.x_test))
    assert clone.weights_signature() == m.weights_signature()


def test_unknown_architecture_rejected(dataset):
    with pytest.raises(ValueError):
        build_model(ModelConfig(name="nope", n_channels=dataset.n_channels,
                                n_samples=dataset.n_samples, n_classes=dataset.n_classes))


def test_unknown_params_rejected(dataset):
    with pytest.raises(ValueError):
        build_model(ModelConfig(name="tcn", n_channels=dataset.n_channels,
                                n_samples=dataset.n_samples, n_classes=dataset.n_classes,
                                params={"not_a_param": 1}))


def test_predict_before_fit_raises(cfg_for, prepared):
    m = build_model(cfg_for("simple_cnn"))
    with pytest.raises(RuntimeError):
        m.predict_proba(prepared.x_test)
