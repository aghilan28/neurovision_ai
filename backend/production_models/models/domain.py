"""Production Model domain entities + closed vocabularies (DRP2-B).

Pure data shapes (JSON-able, content-hashable). No I/O, no orchestration, no
training/evaluation/benchmark logic — this module owns only the *shapes* and the
*closed vocabularies* (no free-form states). The architecture / training / benchmarking /
evaluation / readiness engines produce these records; the service assembles the
immutable ``ProductionModelRecord``.

Mirrors ``backend.model_foundation.models.domain`` so the production-model layer is shaped
exactly like the rest of the platform (NR-6: reuse patterns, don't invent).

Determinism (NR-9/NR-10): every ``signature()`` and content id is a function of the
*deterministic* fields only. Wall-clock-derived performance measures (latency, memory,
training/inference time) are carried as **informational** fields and are deliberately
excluded from every signature, so verdicts reproduce bit-for-bit while timings are still
reported (the platform's offline-inference / P9 convention).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    PRODUCTION_DOMAIN_VERSION, PRODUCTION_TRAINING_VERSION, PRODUCTION_BENCHMARK_VERSION,
    PRODUCTION_EVALUATION_VERSION, PRODUCTION_READINESS_VERSION, PRODUCTION_REGISTRY_VERSION,
    PRODUCTION_VALIDATION_VERSION, DETERMINISTIC_EPOCH, FINGERPRINT_DECIMALS,
)


def _q(x) -> float:
    return round(float(x), FINGERPRINT_DECIMALS)


def _qmap(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        out[k] = _q(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v
    return dict(sorted(out.items()))


# =============================================================================
# Closed vocabularies (no free-form states)
# =============================================================================
class ProductionArchitecture(str, Enum):
    """The closed set of production-candidate architectures.

    The first four are production-grade wrappers around the platform's existing
    deterministic reference models (``backend.model_foundation``); ``HYBRID_EEG`` is a
    new deterministic composition introduced by this layer. The reference models are
    **not removed** — production architectures coexist with them.
    """

    EEGNET = "eegnet"
    DEEPCONVNET = "deepconvnet"
    TEMPORAL_CNN = "temporal_cnn"
    TRANSFORMER_EEG = "transformer_eeg"
    HYBRID_EEG = "hybrid_eeg"


class ModelStatus(str, Enum):
    """A production-candidate model's lifecycle status (content-validation outcome)."""

    CANDIDATE = "candidate"
    QUARANTINED = "quarantined"


class ExperimentStatus(str, Enum):
    COMPLETED = "completed"
    QUARANTINED = "quarantined"


class ReadinessClass(str, Enum):
    NOT_READY = "NOT_READY"
    PARTIALLY_READY = "PARTIALLY_READY"
    READY = "READY"


class ReadinessDimension(str, Enum):
    """The closed set of readiness dimensions (DRP2-G)."""

    TRAINING = "training_readiness"
    EVALUATION = "evaluation_readiness"
    BENCHMARK = "benchmark_readiness"
    REGISTRY = "registry_readiness"
    VALIDATION = "validation_readiness"
    LINEAGE = "lineage_readiness"
    AUDIT = "audit_readiness"


class EntityKind(str, Enum):
    """The kinds of entity tracked in the production-model registry."""

    MODEL = "production_model"
    EXPERIMENT = "training_experiment"
    BENCHMARK = "benchmark"
    EVALUATION = "model_evaluation"
    READINESS = "readiness_assessment"


# =============================================================================
# Identity projection
# =============================================================================
@dataclass(frozen=True)
class ProductionModelIdentity:
    """A production-model identity, content-addressed from its training run (+ arch).
    Never filename-derived."""

    model_id: str
    training_run_id: str
    training_experiment_id: str
    architecture: ProductionArchitecture
    identity_version: str
    domain_version: str = PRODUCTION_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id, "training_run_id": self.training_run_id,
            "training_experiment_id": self.training_experiment_id,
            "architecture": self.architecture.value, "identity_version": self.identity_version,
            "domain_version": self.domain_version,
        }


# =============================================================================
# Versioning
# =============================================================================
@dataclass(frozen=True)
class ModelVersion:
    """A content-addressed model version (chained like the model-foundation version)."""

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


@dataclass(frozen=True)
class BenchmarkVersion:
    """A content-addressed benchmark version (deterministic metrics only; never timings)."""

    version: str
    previous: Optional[str]
    reason: str
    created_at: str = DETERMINISTIC_EPOCH

    @staticmethod
    def compute(metrics_signature: str, previous: Optional[str]) -> str:
        return hash_obj({"metrics": metrics_signature, "previous": previous})

    def to_dict(self) -> dict:
        return {"version": self.version, "previous": self.previous,
                "reason": self.reason, "created_at": self.created_at}


# =============================================================================
# Training experiment
# =============================================================================
@dataclass(frozen=True)
class TrainingExperimentRecord:
    """A reproducible production training experiment (deterministic seed + hyperparameters
    + metrics + history). Captures everything needed to reproduce a training run."""

    experiment_id: str
    architecture: ProductionArchitecture
    dataset_id: str
    training_run_id: str
    seed: int
    hyperparameters: dict
    n_epochs: int
    training_metrics: dict
    training_history: tuple[dict, ...]
    params_fingerprint: str
    n_params: int
    reproducible: bool
    status: ExperimentStatus
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    experiment_version: str = PRODUCTION_TRAINING_VERSION

    def signature(self) -> str:
        return hash_obj({
            "experiment_id": self.experiment_id, "architecture": self.architecture.value,
            "dataset_id": self.dataset_id, "training_run_id": self.training_run_id,
            "seed": self.seed, "hyperparameters": _qmap(self.hyperparameters),
            "n_epochs": self.n_epochs, "training_metrics": _qmap(self.training_metrics),
            "params_fingerprint": self.params_fingerprint, "n_params": self.n_params,
            "reproducible": self.reproducible, "status": self.status.value,
        })

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id, "architecture": self.architecture.value,
            "dataset_id": self.dataset_id, "training_run_id": self.training_run_id,
            "seed": self.seed, "hyperparameters": _qmap(self.hyperparameters),
            "n_epochs": self.n_epochs, "training_metrics": _qmap(self.training_metrics),
            "training_history": [_qmap(h) for h in self.training_history],
            "params_fingerprint": self.params_fingerprint, "n_params": self.n_params,
            "reproducible": self.reproducible, "status": self.status.value,
            "created_at": self.created_at, "lineage_id": self.lineage_id,
            "audit_state": self.audit_state, "experiment_version": self.experiment_version,
            "experiment_signature": self.signature(),
        }


# =============================================================================
# Benchmark
# =============================================================================
@dataclass(frozen=True)
class ModelBenchmarkRecord:
    """A benchmark of one model on the test split.

    ``deterministic_metrics`` (accuracy / precision / recall / f1 / roc_auc / pr_auc /
    ece / brier) are reproducible and enter the signature + id. ``performance`` measures
    (latency / memory / training-time / inference-time) are **informational** — measured
    live and excluded from every signature so verdicts reproduce bit-for-bit (NR-9/NR-10).
    """

    benchmark_id: str
    model_id: str
    architecture: ProductionArchitecture
    dataset_id: str
    split: str
    deterministic_metrics: dict
    performance: dict
    n_samples: int
    n_classes: int
    version: BenchmarkVersion
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    benchmark_version: str = PRODUCTION_BENCHMARK_VERSION

    def metrics_signature(self) -> str:
        """A signature over the deterministic metrics only (never the timings)."""
        return hash_obj({
            "model_id": self.model_id, "architecture": self.architecture.value,
            "dataset_id": self.dataset_id, "split": self.split,
            "deterministic_metrics": _qmap(self.deterministic_metrics),
            "n_samples": self.n_samples, "n_classes": self.n_classes,
        })

    def signature(self) -> str:
        return self.metrics_signature()

    def to_dict(self) -> dict:
        return {
            "benchmark_id": self.benchmark_id, "model_id": self.model_id,
            "architecture": self.architecture.value, "dataset_id": self.dataset_id,
            "split": self.split, "deterministic_metrics": _qmap(self.deterministic_metrics),
            "performance": _qmap(self.performance), "n_samples": self.n_samples,
            "n_classes": self.n_classes, "version": self.version.to_dict(),
            "created_at": self.created_at, "lineage_id": self.lineage_id,
            "benchmark_version": self.benchmark_version,
            "metrics_signature": self.metrics_signature(),
        }


# =============================================================================
# Evaluation (extended analyses)
# =============================================================================
@dataclass(frozen=True)
class ModelEvaluationRecord:
    """Structured, deterministic model evaluation analyses (DRP2-F).

    References the base ``evaluation_id`` (from the model-foundation evaluator) and adds
    confusion / calibration / error / class-distribution / stability / reliability
    analyses. Deterministic and traceable; no images, no UI."""

    model_evaluation_id: str
    model_id: str
    evaluation_id: str
    dataset_id: str
    split: str
    confusion_matrix: tuple[tuple[int, ...], ...]
    calibration_analysis: dict
    error_analysis: dict
    class_distribution_analysis: dict
    stability_analysis: dict
    reliability_analysis: dict
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    evaluation_version: str = PRODUCTION_EVALUATION_VERSION

    def signature(self) -> str:
        return hash_obj({
            "model_evaluation_id": self.model_evaluation_id, "model_id": self.model_id,
            "evaluation_id": self.evaluation_id, "dataset_id": self.dataset_id,
            "split": self.split, "confusion_matrix": [list(r) for r in self.confusion_matrix],
            "calibration_analysis": _qmap(self.calibration_analysis),
            "error_analysis": _qmap(self.error_analysis),
            "class_distribution_analysis": _qmap(self.class_distribution_analysis),
            "stability_analysis": _qmap(self.stability_analysis),
            "reliability_analysis": _qmap(self.reliability_analysis),
        })

    def to_dict(self) -> dict:
        return {
            "model_evaluation_id": self.model_evaluation_id, "model_id": self.model_id,
            "evaluation_id": self.evaluation_id, "dataset_id": self.dataset_id,
            "split": self.split, "confusion_matrix": [list(r) for r in self.confusion_matrix],
            "calibration_analysis": _qmap(self.calibration_analysis),
            "error_analysis": _qmap(self.error_analysis),
            "class_distribution_analysis": _qmap(self.class_distribution_analysis),
            "stability_analysis": _qmap(self.stability_analysis),
            "reliability_analysis": _qmap(self.reliability_analysis),
            "created_at": self.created_at, "lineage_id": self.lineage_id,
            "evaluation_version": self.evaluation_version, "evaluation_signature": self.signature(),
        }


# =============================================================================
# Readiness
# =============================================================================
@dataclass(frozen=True)
class ModelReadinessRecord:
    """A deterministic production-model readiness assessment (DRP2-G).

    A model can only be ``READY`` when training + evaluation + benchmark + registry +
    audit + lineage records exist, a readiness score exists, and validation passes."""

    readiness_id: str
    model_id: str
    score: float
    classification: ReadinessClass
    dimensions: dict
    findings: tuple[str, ...]
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    readiness_version: str = PRODUCTION_READINESS_VERSION

    def signature(self) -> str:
        return hash_obj({
            "readiness_id": self.readiness_id, "model_id": self.model_id, "score": _q(self.score),
            "classification": self.classification.value, "dimensions": _qmap(self.dimensions),
            "findings": list(self.findings),
        })

    def to_dict(self) -> dict:
        return {
            "readiness_id": self.readiness_id, "model_id": self.model_id, "score": _q(self.score),
            "classification": self.classification.value, "dimensions": _qmap(self.dimensions),
            "findings": list(self.findings), "created_at": self.created_at,
            "lineage_id": self.lineage_id, "readiness_version": self.readiness_version,
            "readiness_signature": self.signature(),
        }


# =============================================================================
# Validation projection
# =============================================================================
@dataclass(frozen=True)
class ModelValidationRecord:
    """A persisted projection of the production-model content validation."""

    validation_id: str
    ok: bool
    checks: tuple[tuple, ...]            # (name, passed, detail)
    validation_version: str = PRODUCTION_VALIDATION_VERSION

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


# =============================================================================
# Audit / lineage projections
# =============================================================================
@dataclass(frozen=True)
class ModelAuditRecord:
    """An immutable audit event in the hash-chained production-model audit log
    (the shared ``ImmutableAuditLog`` implementation; no parallel system)."""

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
    """A projection of the shared lineage node attached to a production-model artifact."""

    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


# =============================================================================
# Registry record
# =============================================================================
@dataclass
class ModelRegistryRecord:
    """The production-model registry entry shape (mutated only via governed registry
    methods). Cross-references the shared model-foundation dataset id + model id (no
    parallel dataset / base-model registry is created)."""

    model_id: str
    architecture: str
    dataset_id: str
    training_experiment_id: str
    benchmark_id: str
    model_evaluation_id: str
    readiness_id: str
    base_evaluation_id: str
    case_id: str
    patient_ids: tuple[str, ...]
    status: ModelStatus
    readiness_class: ReadinessClass
    version: str
    owner: str
    creation_date: str
    audit_state: str
    lineage_id: str
    dependencies: tuple[str, ...]
    registry_version: str = PRODUCTION_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({
            "model_id": self.model_id, "architecture": self.architecture,
            "dataset_id": self.dataset_id, "training_experiment_id": self.training_experiment_id,
            "benchmark_id": self.benchmark_id, "model_evaluation_id": self.model_evaluation_id,
            "readiness_id": self.readiness_id, "status": self.status.value,
            "readiness_class": self.readiness_class.value, "version": self.version,
            "lineage_id": self.lineage_id,
        })

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id, "architecture": self.architecture,
            "dataset_id": self.dataset_id, "training_experiment_id": self.training_experiment_id,
            "benchmark_id": self.benchmark_id, "model_evaluation_id": self.model_evaluation_id,
            "readiness_id": self.readiness_id, "base_evaluation_id": self.base_evaluation_id,
            "case_id": self.case_id, "patient_ids": list(self.patient_ids),
            "status": self.status.value, "readiness_class": self.readiness_class.value,
            "version": self.version, "owner": self.owner, "creation_date": self.creation_date,
            "audit_state": self.audit_state, "lineage_id": self.lineage_id,
            "dependencies": list(self.dependencies), "registry_version": self.registry_version,
            "content_signature": self.content_signature(),
        }


# =============================================================================
# The aggregate — the immutable production-candidate Model
# =============================================================================
@dataclass(frozen=True)
class ProductionModelRecord:
    """The production-model aggregate — an **immutable**, versioned, auditable,
    lineage-tracked record of a *production-candidate model*. It binds the training
    experiment, the registered base model id (in the shared model registry), the
    benchmark, the extended evaluation, the readiness assessment, and the validation,
    carrying the model's learned-parameter *fingerprint*, not raw weights."""

    identity: ProductionModelIdentity
    architecture: ProductionArchitecture
    dataset_id: str
    training_experiment_id: str
    base_evaluation_id: str
    benchmark_id: str
    model_evaluation_id: str
    readiness_id: str
    readiness_class: ReadinessClass
    case_id: str
    patient_ids: tuple[str, ...]
    validation: ModelValidationRecord
    params_fingerprint: str
    status: ModelStatus
    version: ModelVersion
    owner: str
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    dependencies: tuple[str, ...] = ()
    domain_version: str = PRODUCTION_DOMAIN_VERSION

    @property
    def model_id(self) -> str:
        return self.identity.model_id

    @property
    def training_run_id(self) -> str:
        return self.identity.training_run_id

    @staticmethod
    def state_signature_of(*, identity, architecture, dataset_id, training_experiment_id,
                           base_evaluation_id, benchmark_id, model_evaluation_id, readiness_id,
                           readiness_class, case_id, patient_ids, validation, params_fingerprint,
                           status, dependencies) -> str:
        return hash_obj({
            "model_id": identity.model_id, "architecture": architecture.value,
            "dataset_id": dataset_id, "training_experiment_id": training_experiment_id,
            "base_evaluation_id": base_evaluation_id, "benchmark_id": benchmark_id,
            "model_evaluation_id": model_evaluation_id, "readiness_id": readiness_id,
            "readiness_class": readiness_class.value, "case_id": case_id,
            "patient_ids": list(patient_ids), "validation_signature": validation.signature(),
            "params_fingerprint": params_fingerprint, "status": status.value,
            "dependencies": list(dependencies),
        })

    def state_signature(self) -> str:
        return self.state_signature_of(
            identity=self.identity, architecture=self.architecture, dataset_id=self.dataset_id,
            training_experiment_id=self.training_experiment_id,
            base_evaluation_id=self.base_evaluation_id, benchmark_id=self.benchmark_id,
            model_evaluation_id=self.model_evaluation_id, readiness_id=self.readiness_id,
            readiness_class=self.readiness_class, case_id=self.case_id,
            patient_ids=self.patient_ids, validation=self.validation,
            params_fingerprint=self.params_fingerprint, status=self.status,
            dependencies=self.dependencies)

    def to_dict(self) -> dict:
        return {
            "domain_version": self.domain_version, "identity": self.identity.to_dict(),
            "architecture": self.architecture.value, "dataset_id": self.dataset_id,
            "training_experiment_id": self.training_experiment_id,
            "base_evaluation_id": self.base_evaluation_id, "benchmark_id": self.benchmark_id,
            "model_evaluation_id": self.model_evaluation_id, "readiness_id": self.readiness_id,
            "readiness_class": self.readiness_class.value, "case_id": self.case_id,
            "patient_ids": list(self.patient_ids), "validation": self.validation.to_dict(),
            "params_fingerprint": self.params_fingerprint, "status": self.status.value,
            "version": self.version.to_dict(), "owner": self.owner, "created_at": self.created_at,
            "lineage_id": self.lineage_id, "audit_head": self.audit_head,
            "dependencies": list(self.dependencies), "state_signature": self.state_signature(),
        }
