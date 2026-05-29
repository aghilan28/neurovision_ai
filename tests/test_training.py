"""Tests for the deterministic training framework + training validation (V1-P5)."""

from __future__ import annotations

import numpy as np
import pytest

from ml.models.base import ModelConfig
from ml.training import Trainer, TrainingConfig
from ml.validation import TrainingValidator, TrainingValidationError
from ml.registry import ModelStatus
from datasets import patient_disjoint_split, SplitConfig


def test_training_run_produces_governed_artifacts(trainer_bundle, dataset, split, model_config):
    trainer, store, registry, lineage = trainer_bundle
    res = trainer.run(dataset=dataset, split=split, model_config=model_config,
                      training_config=TrainingConfig(steps=60))
    # validation passed
    assert res.validation_report["ok"] is True
    # registered
    assert registry.exists(res.model_version)
    assert registry.get(res.model_version).status == ModelStatus.TRAINED
    # artifact integrity + lineage integrity
    assert store.verify(res.weights_ref) is True
    assert lineage.verify_chain(res.lineage_id) is True
    # provenance metadata complete
    md = res.metadata.to_dict()
    for key in ("dataset_version", "split_version", "preprocessing_version",
                "model_version", "architecture_version", "lineage_id"):
        assert md[key]


def test_training_is_reproducible(trainer_bundle, dataset, split, model_config, tmp_path):
    trainer, _, _, _ = trainer_bundle
    res1 = trainer.run(dataset=dataset, split=split, model_config=model_config,
                       training_config=TrainingConfig(steps=60))
    # fresh trainer/store
    from ml.artifacts import ArtifactStore
    from ml.registry import ModelRegistry
    from ml.lineage import LineageTracker
    t2 = Trainer(ArtifactStore(str(tmp_path / "a2")), ModelRegistry(), LineageTracker())
    res2 = t2.run(dataset=dataset, split=split, model_config=model_config,
                  training_config=TrainingConfig(steps=60))
    assert res1.model_version == res2.model_version
    assert res1.lineage_id == res2.lineage_id
    assert res1.weights_ref.checksum == res2.weights_ref.checksum


def test_training_manifest_is_complete(trainer_bundle, dataset, split, model_config):
    trainer, _, _, _ = trainer_bundle
    res = trainer.run(dataset=dataset, split=split, model_config=model_config,
                      training_config=TrainingConfig(steps=40))
    man = res.manifest
    for key in ("version_bundle", "model_config", "training_config", "random_seed",
                "optimizer", "learning_rate", "batch_size", "epochs", "environment", "hardware"):
        assert key in man


def test_validation_catches_class_mismatch(dataset, split):
    bad = ModelConfig(name="simple_cnn", n_channels=dataset.n_channels,
                      n_samples=dataset.n_samples, n_classes=dataset.n_classes + 1, seed=1)
    report = TrainingValidator().pre_training(dataset, split, bad, TrainingConfig(steps=10))
    assert report.ok is False
    names = {c.name for c in report.failures()}
    assert "version_consistency" in names


def test_validation_seven_checks_present(trainer_bundle, dataset, split, model_config):
    trainer, store, _, lineage = trainer_bundle
    res = trainer.run(dataset=dataset, split=split, model_config=model_config,
                      training_config=TrainingConfig(steps=40))
    names = {c["name"] for c in res.validation_report["checks"]}
    expected = {
        "dataset_exists", "patient_disjoint_split_exists", "version_consistency",
        "configuration_validity", "evaluation_compatibility",
        "artifact_integrity", "lineage_integrity",
    }
    assert expected.issubset(names)


def test_training_rejects_non_patient_disjoint_via_pre_validation(dataset, model_config):
    # craft a degenerate split where calibration patient also appears in train
    split = patient_disjoint_split(dataset, SplitConfig())
    object.__setattr__(split, "calibration_patients", split.train_patients[:1] + split.calibration_patients)
    report = TrainingValidator().pre_training(dataset, split, model_config, TrainingConfig(steps=10))
    assert report.ok is False
    assert any(c.name == "patient_disjoint_split_exists" and not c.passed for c in report.checks)
