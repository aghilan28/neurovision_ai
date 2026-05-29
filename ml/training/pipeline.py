"""The reference training pipeline (deterministic, governed, reproducible).

``Trainer.run`` is the single governed path from data to a registered, lineage-
tracked, checksummed model:

  pre-training validation → preprocess+slice (patient-disjoint) → deterministic fit
  → save checksummed weights → compute model version → build version bundle
  → write deterministic manifest → record lineage → register model
  → post-training validation → write training report.

Every output is reproducible and traceable. The pipeline imports only ``ml`` sub-
modules + the foundations (``datasets``/``preprocessing``); it never imports
``evaluation`` (NR-8).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ..version import TRAINING_FRAMEWORK_VERSION, ARCHITECTURE_VERSIONS, DETERMINISTIC_EPOCH
from ..provenance import content_id
from ..models.factory import build_model
from ..models.base import ModelConfig
from ..schemas import MetadataOutput
from ..artifacts import ArtifactStore
from ..registry import ModelRegistry, ModelRecord, ModelStatus
from ..lineage import LineageTracker, VersionBundle, make_lineage_record
from ..validation import TrainingValidator
from ..data import prepare_split, PreparedData
from .config import TrainingConfig
from .manifest import build_training_manifest
from .report import build_training_report


@dataclass
class TrainingResult:
    """Everything produced by a training run (in-memory handles + provenance)."""

    model: Any
    model_version: str
    model_record: ModelRecord
    lineage_id: str
    version_bundle: VersionBundle
    training_history: dict
    validation_report: dict
    training_report: dict
    metadata: MetadataOutput
    prepared: PreparedData
    weights_ref: Any
    manifest: dict


class Trainer:
    """Runs the reference training pipeline."""

    def __init__(
        self,
        artifact_store: ArtifactStore,
        registry: ModelRegistry,
        lineage_tracker: LineageTracker,
        validator: Optional[TrainingValidator] = None,
    ):
        self.store = artifact_store
        self.registry = registry
        self.lineage = lineage_tracker
        self.validator = validator or TrainingValidator()

    def run(
        self,
        *,
        dataset: Any,
        split: Any,
        model_config: ModelConfig,
        training_config: Optional[TrainingConfig] = None,
        preprocessing_config: Any = None,
        owner: Optional[str] = None,
        training_date: str = DETERMINISTIC_EPOCH,
    ) -> TrainingResult:
        training_config = training_config or TrainingConfig()
        owner = owner or training_config.owner

        # 1. pre-training validation (checks 1-4 + evaluation-compatibility contract)
        pre = self.validator.pre_training(dataset, split, model_config, training_config)
        pre.raise_if_failed()

        # 2. preprocess + patient-disjoint slicing
        prepared = prepare_split(dataset, split, preprocessing_config)

        # 3. deterministic training
        model = build_model(model_config)
        history = model.fit(
            prepared.x_train,
            prepared.y_train,
            steps=training_config.steps,
            learning_rate=training_config.learning_rate,
            l2=training_config.l2,
        )

        # 4. compute reproducible model version (binds arch + config + training + weights)
        weights_sig = model.weights_signature()
        model_version = content_id(
            ARCHITECTURE_VERSIONS[model.name],
            {
                "config": model_config.as_dict(),
                "training": training_config.as_dict(),
                "weights": weights_sig,
                "preprocessing": prepared.preprocessing_signature,
                "dataset_version": prepared.dataset_version,
                "split_version": prepared.split_version,
            },
        )

        # 5. save checksummed weights
        weights_ref = self.store.save_weights(f"{model.name}/{model_version}/weights", model.get_weights())

        # 6. version bundle
        version_bundle = VersionBundle(
            dataset_version=prepared.dataset_version,
            preprocessing_version=prepared.preprocessing_version,
            split_version=prepared.split_version,
            training_version=f"{TRAINING_FRAMEWORK_VERSION}+{training_config.signature()}",
            model_version=model_version,
            architecture_version=model.architecture_version,
        )

        # 7. deterministic manifest
        manifest = build_training_manifest(
            model_config=model_config,
            training_config=training_config,
            version_bundle=version_bundle,
            random_seed=model_config.seed,
        )
        manifest_ref = self.store.save_json(f"{model.name}/{model_version}/manifest", manifest)

        # 8. lineage record
        lineage_rec = make_lineage_record(
            kind="training",
            versions=version_bundle,
            inputs={
                "dataset_version": prepared.dataset_version,
                "split_version": prepared.split_version,
                "preprocessing_signature": prepared.preprocessing_signature,
                "model_config_signature": model_config.signature(),
                "training_config_signature": training_config.signature(),
                "n_train": int(prepared.x_train.shape[0]),
                "train_patients": list(split.train_patients),
            },
            outputs={
                "weights": weights_ref.to_dict(),
                "manifest": manifest_ref.to_dict(),
                "weights_signature": weights_sig,
                "model_version": model_version,
            },
            created_at=training_date,
        )
        self.lineage.record(lineage_rec)

        # 9. register the model (no model outside the registry)
        record = ModelRecord(
            model_name=model.name,
            model_version=model_version,
            architecture_version=model.architecture_version,
            training_version=version_bundle.training_version,
            dataset_version=prepared.dataset_version,
            preprocessing_version=prepared.preprocessing_version,
            lineage_id=lineage_rec.lineage_id,
            owner=owner,
            status=ModelStatus.TRAINED,
            weights_signature=weights_sig,
            config_signature=model_config.signature(),
            training_date=training_date,
        )
        self.registry.register(record)

        # 10. post-training validation (artifact + lineage integrity)
        post = self.validator.post_training(self.store, weights_ref, self.lineage, lineage_rec.lineage_id)
        post.raise_if_failed()

        full_validation = pre
        full_validation.checks.extend(post.checks)

        # 11. metadata + training report
        metadata = MetadataOutput(
            model_name=model.name,
            model_version=model_version,
            architecture_version=model.architecture_version,
            preprocessing_version=prepared.preprocessing_version,
            dataset_version=prepared.dataset_version,
            split_version=prepared.split_version,
            training_version=version_bundle.training_version,
            lineage_id=lineage_rec.lineage_id,
        )
        report = build_training_report(
            model_name=model.name,
            model_version=model_version,
            architecture_spec=model.architecture_spec(),
            version_bundle=version_bundle.to_dict(),
            training_history=history.to_dict(),
            validation_report=full_validation.to_dict(),
            lineage_id=lineage_rec.lineage_id,
            artifacts={"weights": weights_ref.to_dict(), "manifest": manifest_ref.to_dict()},
            manifest=manifest,
        )
        self.store.save_json(f"{model.name}/{model_version}/training_report", report)

        return TrainingResult(
            model=model,
            model_version=model_version,
            model_record=record,
            lineage_id=lineage_rec.lineage_id,
            version_bundle=version_bundle,
            training_history=history.to_dict(),
            validation_report=full_validation.to_dict(),
            training_report=report,
            metadata=metadata,
            prepared=prepared,
            weights_ref=weights_ref,
            manifest=manifest,
        )
