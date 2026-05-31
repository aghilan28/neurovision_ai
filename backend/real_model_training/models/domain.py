"""Real Model Training domain entities + closed vocabularies (Track 2).

Pure, JSON-able, content-hashable records describing the **real** training lifecycle:
windowed real-EEG training datasets, training runs/experiments, evaluations, benchmarks,
comparisons, and serving readiness. No I/O and no orchestration here — only the shapes and
the closed vocabularies (NR-6: reuse the platform domain-model shape).

Determinism (NR-9/NR-10): every ``signature()`` / content id is a function of the
deterministic fields only. Wall-clock performance measures (latency / memory / train /
inference time) are carried as informational fields and excluded from every signature.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    FINGERPRINT_DECIMALS, TRAINING_BENCHMARK_VERSION, TRAINING_COMPARISON_VERSION,
    TRAINING_DATASET_VERSION, TRAINING_DOMAIN_VERSION, TRAINING_EVALUATION_VERSION,
    TRAINING_EXPERIMENT_VERSION, TRAINING_READINESS_VERSION, TRAINING_REGISTRY_VERSION,
    DETERMINISTIC_EPOCH,
)


def _q(x: float) -> float:
    return round(float(x), FINGERPRINT_DECIMALS)


def _qmap(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        out[k] = _q(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v
    return dict(sorted(out.items()))


# =============================================================================
# Closed vocabularies
# =============================================================================
class Architecture(str, Enum):
    """The five platform architectures trained by Track 2 (reused from production_models)."""

    EEGNET = "eegnet"
    DEEPCONVNET = "deepconvnet"
    TEMPORAL_CNN = "temporal_cnn"
    TRANSFORMER_EEG = "transformer_eeg"
    HYBRID_EEG = "hybrid_eeg"


class SplitStrategy(str, Enum):
    """How the windowed samples are partitioned into train/val/test."""

    PATIENT_DISJOINT = "patient_disjoint"     # whole patients per split (>=2 patients)
    WINDOW_STRATIFIED = "window_stratified"   # class-stratified by window (single subject)


class ServingReadinessClass(str, Enum):
    NOT_READY = "NOT_READY"
    PARTIALLY_READY = "PARTIALLY_READY"
    READY_FOR_SERVING = "READY_FOR_SERVING"


class ReadinessDimension(str, Enum):
    TRAINING = "training_readiness"
    EVALUATION = "evaluation_readiness"
    BENCHMARK = "benchmark_readiness"
    VALIDATION = "validation_readiness"
    REGISTRY = "registry_readiness"
    AUDIT = "audit_readiness"
    LINEAGE = "lineage_readiness"


class ModelStatus(str, Enum):
    CANDIDATE = "candidate"
    QUARANTINED = "quarantined"


class EntityKind(str, Enum):
    DATASET = "training_dataset"
    RECORDING = "training_recording"
    FEATURE_ASSET = "training_feature_asset"
    TRAINING_RUN = "training_run"
    MODEL = "trained_model"
    EVALUATION = "model_evaluation"
    BENCHMARK = "model_benchmark"
    READINESS = "readiness_assessment"
    COMPARISON = "model_comparison"


# =============================================================================
# T2-B — windowing + dataset
# =============================================================================
@dataclass(frozen=True)
class WindowingSpec:
    window_seconds: float
    stride_seconds: float
    sampling_frequency: float
    n_samples_per_window: int
    background_per_seizure: int

    def to_dict(self) -> dict:
        return {"window_seconds": _q(self.window_seconds), "stride_seconds": _q(self.stride_seconds),
                "sampling_frequency": _q(self.sampling_frequency),
                "n_samples_per_window": self.n_samples_per_window,
                "background_per_seizure": self.background_per_seizure}


@dataclass(frozen=True)
class RealTrainingDatasetRecord:
    """A windowed, labelled training dataset derived from real Track-1 recordings."""

    dataset_id: str
    source_dataset_id: str
    source: str
    n_windows: int
    n_features: int
    n_classes: int
    class_names: tuple
    class_distribution: dict
    patient_ids: tuple
    recording_ids: tuple
    split_strategy: SplitStrategy
    patient_disjoint: bool
    n_train: int
    n_val: int
    n_test: int
    windowing: WindowingSpec
    feature_names: tuple
    data_fingerprint: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    dataset_version: str = TRAINING_DATASET_VERSION

    def to_dict(self) -> dict:
        return {"dataset_id": self.dataset_id, "source_dataset_id": self.source_dataset_id,
                "source": self.source, "n_windows": self.n_windows, "n_features": self.n_features,
                "n_classes": self.n_classes, "class_names": list(self.class_names),
                "class_distribution": dict(sorted(self.class_distribution.items())),
                "patient_ids": list(self.patient_ids), "recording_ids": list(self.recording_ids),
                "split_strategy": self.split_strategy.value, "patient_disjoint": self.patient_disjoint,
                "n_train": self.n_train, "n_val": self.n_val, "n_test": self.n_test,
                "windowing": self.windowing.to_dict(), "feature_names": list(self.feature_names),
                "data_fingerprint": self.data_fingerprint, "created_at": self.created_at,
                "lineage_id": self.lineage_id, "audit_state": self.audit_state,
                "dataset_version": self.dataset_version}


# =============================================================================
# T2-D — experiment tracking
# =============================================================================
@dataclass(frozen=True)
class TrainingExperimentRecord:
    experiment_id: str
    architecture: Architecture
    dataset_id: str
    dataset_version: str
    feature_version: str
    training_run_id: str
    model_id: str
    configuration: dict
    hyperparameters: dict
    training_metrics: dict
    evaluation_metrics: dict
    benchmark_metrics: dict
    reproducible: bool
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    experiment_version: str = TRAINING_EXPERIMENT_VERSION

    def signature(self) -> str:
        return hash_obj({"experiment_id": self.experiment_id,
                         "architecture": self.architecture.value, "dataset_id": self.dataset_id,
                         "training_run_id": self.training_run_id, "model_id": self.model_id,
                         "configuration": _qmap(self.configuration),
                         "hyperparameters": _qmap(self.hyperparameters),
                         "training_metrics": _qmap(self.training_metrics),
                         "evaluation_metrics": _qmap(self.evaluation_metrics),
                         "benchmark_metrics": _qmap(self.benchmark_metrics),
                         "reproducible": self.reproducible})

    def to_dict(self) -> dict:
        return {"experiment_id": self.experiment_id, "architecture": self.architecture.value,
                "dataset_id": self.dataset_id, "dataset_version": self.dataset_version,
                "feature_version": self.feature_version, "training_run_id": self.training_run_id,
                "model_id": self.model_id, "configuration": _qmap(self.configuration),
                "hyperparameters": _qmap(self.hyperparameters),
                "training_metrics": _qmap(self.training_metrics),
                "evaluation_metrics": _qmap(self.evaluation_metrics),
                "benchmark_metrics": _qmap(self.benchmark_metrics), "reproducible": self.reproducible,
                "created_at": self.created_at, "lineage_id": self.lineage_id,
                "experiment_version": self.experiment_version, "experiment_signature": self.signature()}


# =============================================================================
# T2-E — evaluation projection (extends DRP-2 with sensitivity/specificity)
# =============================================================================
@dataclass(frozen=True)
class EvaluationSummaryRecord:
    evaluation_id: str
    model_id: str
    dataset_id: str
    split: str
    metrics: dict                          # accuracy/precision/recall/f1/roc_auc/pr_auc/sens/spec
    confusion_matrix: tuple
    calibration: dict
    reliability: dict
    base_evaluation_id: str
    model_evaluation_id: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    evaluation_version: str = TRAINING_EVALUATION_VERSION

    def signature(self) -> str:
        return hash_obj({"evaluation_id": self.evaluation_id, "model_id": self.model_id,
                         "dataset_id": self.dataset_id, "split": self.split,
                         "metrics": _qmap(self.metrics),
                         "confusion_matrix": [list(r) for r in self.confusion_matrix],
                         "calibration": _qmap(self.calibration)})

    def to_dict(self) -> dict:
        return {"evaluation_id": self.evaluation_id, "model_id": self.model_id,
                "dataset_id": self.dataset_id, "split": self.split, "metrics": _qmap(self.metrics),
                "confusion_matrix": [list(r) for r in self.confusion_matrix],
                "calibration": _qmap(self.calibration), "reliability": _qmap(self.reliability),
                "base_evaluation_id": self.base_evaluation_id,
                "model_evaluation_id": self.model_evaluation_id, "created_at": self.created_at,
                "lineage_id": self.lineage_id, "evaluation_version": self.evaluation_version,
                "evaluation_signature": self.signature()}


# =============================================================================
# T2-F — benchmark projection
# =============================================================================
@dataclass(frozen=True)
class BenchmarkSummaryRecord:
    benchmark_id: str
    model_id: str
    architecture: Architecture
    dataset_id: str
    split: str
    deterministic_metrics: dict
    performance: dict                      # informational; never hashed
    n_samples: int
    n_classes: int
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    benchmark_version: str = TRAINING_BENCHMARK_VERSION

    def metrics_signature(self) -> str:
        return hash_obj({"model_id": self.model_id, "architecture": self.architecture.value,
                         "dataset_id": self.dataset_id, "split": self.split,
                         "deterministic_metrics": _qmap(self.deterministic_metrics),
                         "n_samples": self.n_samples, "n_classes": self.n_classes})

    def to_dict(self) -> dict:
        return {"benchmark_id": self.benchmark_id, "model_id": self.model_id,
                "architecture": self.architecture.value, "dataset_id": self.dataset_id,
                "split": self.split, "deterministic_metrics": _qmap(self.deterministic_metrics),
                "performance": _qmap(self.performance), "n_samples": self.n_samples,
                "n_classes": self.n_classes, "created_at": self.created_at,
                "lineage_id": self.lineage_id, "benchmark_version": self.benchmark_version,
                "metrics_signature": self.metrics_signature()}


# =============================================================================
# T2-H — serving readiness
# =============================================================================
@dataclass(frozen=True)
class ServingReadinessRecord:
    readiness_id: str
    model_id: str
    score: float
    classification: ServingReadinessClass
    dimensions: dict
    findings: tuple
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    readiness_version: str = TRAINING_READINESS_VERSION

    def to_dict(self) -> dict:
        return {"readiness_id": self.readiness_id, "model_id": self.model_id, "score": _q(self.score),
                "classification": self.classification.value,
                "dimensions": dict(sorted(self.dimensions.items())), "findings": list(self.findings),
                "created_at": self.created_at, "lineage_id": self.lineage_id,
                "readiness_version": self.readiness_version}


# =============================================================================
# T2-G — comparison projection
# =============================================================================
@dataclass(frozen=True)
class ComparisonRecord:
    comparison_id: str
    dataset_id: str
    n_models: int
    metrics: tuple
    ranking: tuple
    best_per_metric: dict
    recommended_model: Optional[str]
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    comparison_version: str = TRAINING_COMPARISON_VERSION

    def to_dict(self) -> dict:
        return {"comparison_id": self.comparison_id, "dataset_id": self.dataset_id,
                "n_models": self.n_models, "metrics": list(self.metrics),
                "ranking": list(self.ranking), "best_per_metric": self.best_per_metric,
                "recommended_model": self.recommended_model, "created_at": self.created_at,
                "lineage_id": self.lineage_id, "comparison_version": self.comparison_version}


# =============================================================================
# Validation projection
# =============================================================================
@dataclass(frozen=True)
class TrainingValidationRecord:
    validation_id: str
    ok: bool
    checks: tuple                           # (name, passed, detail)

    @property
    def n_checks(self) -> int:
        return len(self.checks)

    def signature(self) -> str:
        return hash_obj({"ok": self.ok, "checks": [[n, bool(p)] for n, p, _ in self.checks]})

    def to_dict(self) -> dict:
        return {"validation_id": self.validation_id, "ok": self.ok, "n_checks": self.n_checks,
                "checks": [{"name": n, "passed": bool(p), "detail": d} for n, p, d in self.checks],
                "validation_signature": self.signature()}


# =============================================================================
# The aggregate — a trained, evaluated, benchmarked candidate model
# =============================================================================
@dataclass(frozen=True)
class CandidateModelRecord:
    model_id: str
    architecture: Architecture
    dataset_id: str
    training_run_id: str
    experiment_id: str
    evaluation_id: str
    benchmark_id: str
    readiness_id: str
    readiness_class: ServingReadinessClass
    params_fingerprint: str
    reproducible: bool
    patient_ids: tuple
    validation: TrainingValidationRecord
    status: ModelStatus
    headline_metrics: dict
    owner: str = "model-training-ops"
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    domain_version: str = TRAINING_DOMAIN_VERSION

    @property
    def ready_for_serving(self) -> bool:
        return self.readiness_class == ServingReadinessClass.READY_FOR_SERVING

    def to_dict(self) -> dict:
        return {"model_id": self.model_id, "architecture": self.architecture.value,
                "dataset_id": self.dataset_id, "training_run_id": self.training_run_id,
                "experiment_id": self.experiment_id, "evaluation_id": self.evaluation_id,
                "benchmark_id": self.benchmark_id, "readiness_id": self.readiness_id,
                "readiness_class": self.readiness_class.value,
                "params_fingerprint": self.params_fingerprint, "reproducible": self.reproducible,
                "patient_ids": list(self.patient_ids), "validation": self.validation.to_dict(),
                "status": self.status.value, "headline_metrics": _qmap(self.headline_metrics),
                "owner": self.owner, "created_at": self.created_at, "lineage_id": self.lineage_id,
                "audit_head": self.audit_head, "domain_version": self.domain_version,
                "ready_for_serving": self.ready_for_serving}


# =============================================================================
# Registry / audit / lineage projections
# =============================================================================
@dataclass
class TrainingRegistryRecord:
    entity_kind: EntityKind
    entity_id: str
    status: str
    version: str
    owner: str
    creation_date: str
    audit_state: str
    lineage_id: str
    dependencies: tuple = ()
    registry_version: str = TRAINING_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"entity_kind": self.entity_kind.value, "entity_id": self.entity_id,
                         "status": self.status, "version": self.version,
                         "lineage_id": self.lineage_id, "audit_state": self.audit_state})

    def to_dict(self) -> dict:
        return {"entity_kind": self.entity_kind.value, "entity_id": self.entity_id,
                "status": self.status, "version": self.version, "owner": self.owner,
                "creation_date": self.creation_date, "audit_state": self.audit_state,
                "lineage_id": self.lineage_id, "dependencies": list(self.dependencies),
                "registry_version": self.registry_version,
                "content_signature": self.content_signature()}


@dataclass(frozen=True)
class TrainingAuditRecord:
    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {"seq": self.seq, "kind": self.kind, "payload": self.payload,
                "prev_hash": self.prev_hash, "event_hash": self.event_hash,
                "created_at": self.created_at}


__all__ = [
    "Architecture", "SplitStrategy", "ServingReadinessClass", "ReadinessDimension", "ModelStatus",
    "EntityKind", "WindowingSpec", "RealTrainingDatasetRecord", "TrainingExperimentRecord",
    "EvaluationSummaryRecord", "BenchmarkSummaryRecord", "ServingReadinessRecord",
    "ComparisonRecord", "TrainingValidationRecord", "CandidateModelRecord", "TrainingRegistryRecord",
    "TrainingAuditRecord",
]
