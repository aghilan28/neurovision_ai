"""Shared pytest fixtures for the NeuroVision AI V1 test suite.

Uses a small, fast, deterministic synthetic dataset so the whole suite runs
quickly while still exercising patient-disjoint splitting, training, evaluation,
and the full uncertainty stack.
"""

from __future__ import annotations

import numpy as np
import pytest

from datasets import generate_dataset, SyntheticConfig, patient_disjoint_split, SplitConfig
from ml.models.base import ModelConfig
from ml.models.factory import build_model
from ml.data import prepare_split
from ml.artifacts import ArtifactStore
from ml.registry import ModelRegistry
from ml.lineage import LineageTracker
from ml.training import Trainer, TrainingConfig

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def synthetic_config() -> SyntheticConfig:
    return SyntheticConfig(n_patients=12, windows_per_patient=18, seed=20240501)


@pytest.fixture(scope="session")
def dataset(synthetic_config):
    return generate_dataset(synthetic_config)


@pytest.fixture(scope="session")
def split(dataset):
    s = patient_disjoint_split(dataset, SplitConfig())
    s.assert_patient_disjoint()
    return s


@pytest.fixture(scope="session")
def prepared(dataset, split):
    return prepare_split(dataset, split)


@pytest.fixture(scope="session")
def training_config() -> TrainingConfig:
    return TrainingConfig(steps=80)


@pytest.fixture
def model_config(dataset):
    return ModelConfig(
        name="simple_cnn",
        n_channels=dataset.n_channels,
        n_samples=dataset.n_samples,
        n_classes=dataset.n_classes,
        seed=7,
    )


@pytest.fixture
def fresh_model(model_config):
    return build_model(model_config)


@pytest.fixture
def trained_model(prepared, model_config):
    m = build_model(model_config)
    m.fit(prepared.x_train, prepared.y_train, steps=80)
    return m


@pytest.fixture
def trainer_bundle(tmp_path):
    store = ArtifactStore(str(tmp_path / "artifacts"))
    registry = ModelRegistry()
    lineage = LineageTracker()
    return Trainer(store, registry, lineage), store, registry, lineage


@pytest.fixture(scope="session")
def trained_for_uncertainty(prepared, dataset):
    """A trained model + calibration/test logits for uncertainty tests."""
    cfg = ModelConfig(name="tcn", n_channels=dataset.n_channels, n_samples=dataset.n_samples,
                      n_classes=dataset.n_classes, seed=11)
    m = build_model(cfg)
    m.fit(prepared.x_train, prepared.y_train, steps=120)
    calib_logits = m.forward_logits(prepared.x_calibration)
    test_logits = m.forward_logits(prepared.x_test)
    return {
        "model": m,
        "calib_logits": calib_logits,
        "test_logits": test_logits,
        "calib_labels": prepared.y_calibration,
        "test_labels": prepared.y_test,
        "class_names": dataset.class_names,
    }



# --- offline inference + research app fixtures (V1-P7 / V1-P8) ----------------
from backend.offline_inference import InferenceOrchestrator, PipelineConfig, FakeClock


def _small_pipeline_config() -> PipelineConfig:
    return PipelineConfig(
        synthetic=SyntheticConfig(n_patients=12, windows_per_patient=18),
        training=TrainingConfig(steps=60),
        model_name="tcn",
        alpha=0.1,
    )


@pytest.fixture(scope="session")
def offline_config() -> PipelineConfig:
    return _small_pipeline_config()


@pytest.fixture(scope="session")
def offline_run(tmp_path_factory, offline_config):
    """Run the orchestrator once per session; return (OrchestratorResult, output_dir)."""
    out = tmp_path_factory.mktemp("offline_run")
    orch = InferenceOrchestrator(offline_config, output_dir=str(out), clock=FakeClock())
    result = orch.run()
    return result, str(out)



# --- EEG Foundation fixtures (Productization P1) -----------------------------
@pytest.fixture(scope="session")
def eeg_fixtures() -> dict:
    """Ensure the committed EEG fixtures exist; return ``{name: path}``.

    Files live in ``tests/fixtures/eeg/`` and are regenerated deterministically if
    any are missing (e.g. on a fresh checkout). See ``tests/_eeg_fixtures.py``.
    """
    from _eeg_fixtures import generate_fixtures

    dest = str(REPO_ROOT / "tests" / "fixtures" / "eeg")
    return generate_fixtures(dest)
