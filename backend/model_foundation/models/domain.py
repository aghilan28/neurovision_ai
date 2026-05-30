"""Model Foundation domain entities + closed vocabularies (Productization P4).

Pure data shapes (JSON-able, content-hashable). No I/O, no orchestration, no
training/evaluation logic — this module owns only the *shapes* and the *closed
vocabularies* (no free-form states). The datasets/training/evaluation/experiment
engines produce these records; the service assembles the immutable ``ModelRecord``.

Mirrors ``backend.feature_engineering.models.domain`` so the model layer is shaped
exactly like the rest of the platform (NR-6: reuse patterns, don't invent).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    MODEL_DOMAIN_VERSION, MODEL_DATASET_VERSION, MODEL_TRAINING_VERSION,
    MODEL_EVALUATION_VERSION, MODEL_EXPERIMENT_VERSION, MODEL_REGISTRY_VERSION,
    MODEL_VALIDATION_VERSION, DETERMINISTIC_EPOCH, FINGERPRINT_DECIMALS,
)


def _q(x: float) -> float:
    return round(float(x), FINGERPRINT_DECIMALS)


def _qmap(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        out[k] = _q(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v
    return dict(sorted(out.items()))


# =============================================================================
# Closed vocabularies (no free-form states)
# =============================================================================
class ModelArchitecture(str, Enum):
    """The closed set of baseline architectures (deterministic pure-NumPy reference
    implementations — see ADR-0017)."""

    EEGNET = "eegnet"
    DEEPCONVNET = "deepconvnet"
    TEMPORAL_CNN = "temporal_cnn"
    TRANSFORMER = "transformer"


class DatasetSource(str, Enum):
    """The closed set of dataset sources. External neuro datasets are integrated via a
    manifest framework (never downloaded); the trainable source is feature assets."""

    TUH_EEG = "tuh_eeg"
    CHB_MIT = "chb_mit"
    TEMPLE_EEG = "temple_eeg"
    FEATURE_ASSETS = "feature_assets"


class SplitName(str, Enum):
    TRAIN = "train"
    VAL = "val"
    TEST = "test"


class DatasetStatus(str, Enum):
    REGISTERED = "registered"
    QUARANTINED = "quarantined"


class ModelStatus(str, Enum):
    TRAINED = "trained"
    QUARANTINED = "quarantined"


class ExperimentStatus(str, Enum):
    COMPLETED = "completed"
    QUARANTINED = "quarantined"


# =============================================================================
# Identity projection
# =============================================================================
@dataclass(frozen=True)
class ModelIdentity:
    """A model identity, content-addressed from its training run (+ architecture).
    Never filename-derived."""

    model_id: str
    training_run_id: str
    architecture: ModelArchitecture
    identity_version: str
    domain_version: str = MODEL_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id, "training_run_id": self.training_run_id,
            "architecture": self.architecture.value, "identity_version": self.identity_version,
            "domain_version": self.domain_version,
        }


# =============================================================================
# Dataset
# =============================================================================
@dataclass(frozen=True)
class DataSplit:
    """A deterministic, patient-disjoint train/val/test split (sample-id lists)."""

    train: tuple[str, ...]
    val: tuple[str, ...]
    test: tuple[str, ...]
    patient_disjoint: bool

    def to_dict(self) -> dict:
        return {
            "train": list(self.train), "val": list(self.val), "test": list(self.test),
            "n_train": len(self.train), "n_val": len(self.val), "n_test": len(self.test),
            "patient_disjoint": self.patient_disjoint,
        }


@dataclass(frozen=True)
class DatasetRecord:
    """Metadata of a registered dataset (the numeric arrays live in a DatasetBundle).

    For external sources (TUH/CHB-MIT/Temple) this is registered from a manifest with
    no data; for the ``feature_assets`` source it is built from registered feature
    assets and carries a ``data_fingerprint`` of the assembled (X, y)."""

    dataset_id: str
    source: DatasetSource
    name: str
    n_samples: int
    n_features: int
    feature_names: tuple[str, ...]
    class_labels: tuple[int, ...]
    class_distribution: dict
    patient_ids: tuple[str, ...]
    feature_asset_ids: tuple[str, ...]
    split: Optional[DataSplit]
    data_fingerprint: str
    status: DatasetStatus
    source_metadata: dict = field(default_factory=dict)
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    dataset_version: str = MODEL_DATASET_VERSION

    def signature(self) -> str:
        return hash_obj({
            "dataset_id": self.dataset_id, "source": self.source.value, "name": self.name,
            "n_samples": self.n_samples, "n_features": self.n_features,
            "feature_names": list(self.feature_names), "class_distribution": _qmap(self.class_distribution),
            "patient_ids": list(self.patient_ids), "feature_asset_ids": list(self.feature_asset_ids),
            "split": self.split.to_dict() if self.split else None,
            "data_fingerprint": self.data_fingerprint, "status": self.status.value,
        })

    def to_dict(self) -> dict:
        return {
            "dataset_id": self.dataset_id, "source": self.source.value, "name": self.name,
            "n_samples": self.n_samples, "n_features": self.n_features,
            "feature_names": list(self.feature_names), "class_labels": list(self.class_labels),
            "class_distribution": _qmap(self.class_distribution), "patient_ids": list(self.patient_ids),
            "feature_asset_ids": list(self.feature_asset_ids),
            "split": self.split.to_dict() if self.split else None,
            "data_fingerprint": self.data_fingerprint, "status": self.status.value,
            "source_metadata": dict(sorted(self.source_metadata.items())),
            "created_at": self.created_at, "lineage_id": self.lineage_id,
            "audit_state": self.audit_state, "dataset_version": self.dataset_version,
            "dataset_signature": self.signature(),
        }


# =============================================================================
# Training run
# =============================================================================
@dataclass(frozen=True)
class TrainingRunRecord:
    """A reproducible training run (deterministic seed + hyperparameters + metrics)."""

    training_run_id: str
    architecture: ModelArchitecture
    dataset_id: str
    seed: int
    hyperparameters: dict
    n_epochs: int
    training_metrics: dict
    training_history: tuple[dict, ...]
    params_fingerprint: str
    n_params: int
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    training_version: str = MODEL_TRAINING_VERSION

    def signature(self) -> str:
        return hash_obj({
            "training_run_id": self.training_run_id, "architecture": self.architecture.value,
            "dataset_id": self.dataset_id, "seed": self.seed,
            "hyperparameters": _qmap(self.hyperparameters), "n_epochs": self.n_epochs,
            "training_metrics": _qmap(self.training_metrics), "params_fingerprint": self.params_fingerprint,
            "n_params": self.n_params,
        })

    def to_dict(self) -> dict:
        return {
            "training_run_id": self.training_run_id, "architecture": self.architecture.value,
            "dataset_id": self.dataset_id, "seed": self.seed,
            "hyperparameters": _qmap(self.hyperparameters), "n_epochs": self.n_epochs,
            "training_metrics": _qmap(self.training_metrics),
            "training_history": [_qmap(h) for h in self.training_history],
            "params_fingerprint": self.params_fingerprint, "n_params": self.n_params,
            "created_at": self.created_at, "lineage_id": self.lineage_id,
            "audit_state": self.audit_state, "training_version": self.training_version,
            "training_signature": self.signature(),
        }


# =============================================================================
# Evaluation
# =============================================================================
@dataclass(frozen=True)
class EvaluationRecord:
    """Deterministic evaluation of a trained model on a split."""

    evaluation_id: str
    training_run_id: str
    dataset_id: str
    split: SplitName
    metrics: dict
    confusion_matrix: tuple[tuple[int, ...], ...]
    calibration: dict
    uncertainty: dict
    dataset_metrics: dict
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    evaluation_version: str = MODEL_EVALUATION_VERSION

    def signature(self) -> str:
        return hash_obj({
            "evaluation_id": self.evaluation_id, "training_run_id": self.training_run_id,
            "dataset_id": self.dataset_id, "split": self.split.value, "metrics": _qmap(self.metrics),
            "confusion_matrix": [list(r) for r in self.confusion_matrix],
            "calibration": _qmap(self.calibration), "uncertainty": _qmap(self.uncertainty),
        })

    def to_dict(self) -> dict:
        return {
            "evaluation_id": self.evaluation_id, "training_run_id": self.training_run_id,
            "dataset_id": self.dataset_id, "split": self.split.value, "metrics": _qmap(self.metrics),
            "confusion_matrix": [list(r) for r in self.confusion_matrix],
            "calibration": _qmap(self.calibration), "uncertainty": _qmap(self.uncertainty),
            "dataset_metrics": _qmap(self.dataset_metrics), "created_at": self.created_at,
            "lineage_id": self.lineage_id, "evaluation_version": self.evaluation_version,
            "evaluation_signature": self.signature(),
        }


# =============================================================================
# Experiment
# =============================================================================
@dataclass(frozen=True)
class ExperimentRecord:
    """A reproducible experiment binding dataset + model + config + metrics + artifacts."""

    experiment_id: str
    name: str
    dataset_id: str
    architecture: ModelArchitecture
    configuration: dict
    training_run_id: str
    evaluation_id: str
    metrics: dict
    artifact_refs: tuple[str, ...]
    status: ExperimentStatus
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    experiment_version: str = MODEL_EXPERIMENT_VERSION

    def signature(self) -> str:
        return hash_obj({
            "experiment_id": self.experiment_id, "name": self.name, "dataset_id": self.dataset_id,
            "architecture": self.architecture.value, "configuration": _qmap(self.configuration),
            "training_run_id": self.training_run_id, "evaluation_id": self.evaluation_id,
            "metrics": _qmap(self.metrics), "artifact_refs": list(self.artifact_refs),
            "status": self.status.value,
        })

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id, "name": self.name, "dataset_id": self.dataset_id,
            "architecture": self.architecture.value, "configuration": _qmap(self.configuration),
            "training_run_id": self.training_run_id, "evaluation_id": self.evaluation_id,
            "metrics": _qmap(self.metrics), "artifact_refs": list(self.artifact_refs),
            "status": self.status.value, "created_at": self.created_at, "lineage_id": self.lineage_id,
            "audit_state": self.audit_state, "experiment_version": self.experiment_version,
            "experiment_signature": self.signature(),
        }


# =============================================================================
# Metadata / validation / audit / lineage / version
# =============================================================================
@dataclass(frozen=True)
class ModelMetadata:
    """Normalized, deterministic metadata for a model."""

    architecture: ModelArchitecture
    dataset_id: str
    dataset_source: str
    n_features: int
    n_classes: int
    class_labels: tuple[int, ...]
    n_params: int
    seed: int
    hyperparameters: dict
    train_accuracy: float
    eval_accuracy: float
    eval_f1: float
    n_train: int
    n_val: int
    n_test: int
    metadata_version: str = MODEL_DOMAIN_VERSION

    def signature(self) -> str:
        return hash_obj(self._core())

    def _core(self) -> dict:
        return {
            "architecture": self.architecture.value, "dataset_id": self.dataset_id,
            "dataset_source": self.dataset_source, "n_features": self.n_features,
            "n_classes": self.n_classes, "class_labels": list(self.class_labels),
            "n_params": self.n_params, "seed": self.seed,
            "hyperparameters": _qmap(self.hyperparameters), "train_accuracy": _q(self.train_accuracy),
            "eval_accuracy": _q(self.eval_accuracy), "eval_f1": _q(self.eval_f1),
            "n_train": self.n_train, "n_val": self.n_val, "n_test": self.n_test,
        }

    def to_dict(self) -> dict:
        return {**self._core(), "metadata_version": self.metadata_version,
                "metadata_signature": self.signature()}


@dataclass(frozen=True)
class ModelValidationRecord:
    """A persisted projection of the model validation (build-time content checks)."""

    validation_id: str
    ok: bool
    checks: tuple[tuple, ...]            # (name, passed, detail)
    validation_version: str = MODEL_VALIDATION_VERSION

    @property
    def n_checks(self) -> int:
        return len(self.checks)

    def signature(self) -> str:
        return hash_obj({"ok": self.ok, "checks": [[n, bool(p)] for n, p, _ in self.checks]})

    def to_dict(self) -> dict:
        return {
            "validation_id": self.validation_id, "ok": self.ok, "n_checks": self.n_checks,
            "checks": [{"name": n, "passed": bool(p), "detail": d} for n, p, d in self.checks],
            "validation_version": self.validation_version, "validation_signature": self.signature(),
        }


@dataclass(frozen=True)
class ModelAuditRecord:
    """An immutable audit event in the hash-chained model audit log (shared log)."""

    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {
            "seq": self.seq, "kind": self.kind, "payload": self.payload,
            "prev_hash": self.prev_hash, "event_hash": self.event_hash, "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ModelLineageRecord:
    """A projection of the shared lineage node attached to a model artifact."""

    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


@dataclass(frozen=True)
class ModelVersion:
    """A content-addressed model version (chained like FeatureVersion)."""

    version: str
    previous: Optional[str]
    reason: str
    created_at: str = DETERMINISTIC_EPOCH

    @staticmethod
    def compute(state_signature: str, previous: Optional[str]) -> str:
        return hash_obj({"state": state_signature, "previous": previous})

    def to_dict(self) -> dict:
        return {"version": self.version, "previous": self.previous,
                "reason": self.reason, "created_at": self.created_at}


# =============================================================================
# Registry record
# =============================================================================
@dataclass
class ModelRegistryRecord:
    """The registry entry shape (mutated only via governed registry methods)."""

    model_id: str
    architecture: str
    dataset_id: str
    training_run_id: str
    evaluation_id: str
    experiment_id: str
    case_id: str
    patient_ids: tuple[str, ...]
    status: ModelStatus
    version: str
    owner: str
    creation_date: str
    audit_state: str
    lineage_id: str
    dependencies: tuple[str, ...]
    model_registry_version: str = MODEL_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({
            "model_id": self.model_id, "architecture": self.architecture, "dataset_id": self.dataset_id,
            "training_run_id": self.training_run_id, "evaluation_id": self.evaluation_id,
            "experiment_id": self.experiment_id, "status": self.status.value, "version": self.version,
            "lineage_id": self.lineage_id,
        })

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id, "architecture": self.architecture, "dataset_id": self.dataset_id,
            "training_run_id": self.training_run_id, "evaluation_id": self.evaluation_id,
            "experiment_id": self.experiment_id, "case_id": self.case_id,
            "patient_ids": list(self.patient_ids), "status": self.status.value, "version": self.version,
            "owner": self.owner, "creation_date": self.creation_date, "audit_state": self.audit_state,
            "lineage_id": self.lineage_id, "dependencies": list(self.dependencies),
            "model_registry_version": self.model_registry_version,
            "content_signature": self.content_signature(),
        }


# =============================================================================
# The aggregate — the immutable trained Model
# =============================================================================
@dataclass(frozen=True)
class ModelRecord:
    """The model aggregate — an **immutable**, versioned, auditable, lineage-tracked
    record of a *validated trained model*. References its dataset, training run,
    evaluation, and experiment; carries normalized metadata, the validation record,
    status, version, owner, lineage node, and audit-log head. It carries the model's
    learned-parameter *fingerprint*, not raw weights."""

    identity: ModelIdentity
    architecture: ModelArchitecture
    dataset_id: str
    training_run_id: str
    evaluation_id: str
    experiment_id: str
    case_id: str
    patient_ids: tuple[str, ...]
    metadata: ModelMetadata
    validation: ModelValidationRecord
    params_fingerprint: str
    status: ModelStatus
    version: ModelVersion
    owner: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    dependencies: tuple[str, ...] = ()
    domain_version: str = MODEL_DOMAIN_VERSION

    @property
    def model_id(self) -> str:
        return self.identity.model_id

    @staticmethod
    def state_signature_of(*, identity, architecture, dataset_id, training_run_id, evaluation_id,
                           experiment_id, case_id, patient_ids, metadata, validation,
                           params_fingerprint, status, dependencies) -> str:
        return hash_obj({
            "model_id": identity.model_id, "architecture": architecture.value,
            "dataset_id": dataset_id, "training_run_id": training_run_id,
            "evaluation_id": evaluation_id, "experiment_id": experiment_id, "case_id": case_id,
            "patient_ids": list(patient_ids), "metadata_signature": metadata.signature(),
            "validation_signature": validation.signature(), "params_fingerprint": params_fingerprint,
            "status": status.value, "dependencies": list(dependencies),
        })

    def state_signature(self) -> str:
        return self.state_signature_of(
            identity=self.identity, architecture=self.architecture, dataset_id=self.dataset_id,
            training_run_id=self.training_run_id, evaluation_id=self.evaluation_id,
            experiment_id=self.experiment_id, case_id=self.case_id, patient_ids=self.patient_ids,
            metadata=self.metadata, validation=self.validation,
            params_fingerprint=self.params_fingerprint, status=self.status,
            dependencies=self.dependencies)

    def to_dict(self) -> dict:
        return {
            "domain_version": self.domain_version, "identity": self.identity.to_dict(),
            "architecture": self.architecture.value, "dataset_id": self.dataset_id,
            "training_run_id": self.training_run_id, "evaluation_id": self.evaluation_id,
            "experiment_id": self.experiment_id, "case_id": self.case_id,
            "patient_ids": list(self.patient_ids), "metadata": self.metadata.to_dict(),
            "validation": self.validation.to_dict(), "params_fingerprint": self.params_fingerprint,
            "status": self.status.value, "version": self.version.to_dict(), "owner": self.owner,
            "created_at": self.created_at, "lineage_id": self.lineage_id, "audit_head": self.audit_head,
            "dependencies": list(self.dependencies), "state_signature": self.state_signature(),
        }
