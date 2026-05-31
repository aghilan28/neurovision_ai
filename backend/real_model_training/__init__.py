"""``backend/real_model_training`` — Real Model Training & Benchmark (Track 2).

Turns the **real datasets** acquired by Track 1 into **real trained models**: it windows the
real recordings into labelled samples, trains the platform's five architectures (EEGNet /
DeepConvNet / Temporal CNN / Transformer EEG / Hybrid EEG) on that real data, evaluates +
benchmarks + compares them, and scores **serving readiness** (NOT_READY / PARTIALLY_READY /
READY_FOR_SERVING) with complete lineage + audit.

It REUSES the existing training/evaluation/benchmark engines (``backend.production_models`` +
``backend.model_foundation``), the Track-1 ``RealDatasetService``, the shared ``ml.lineage``
tracker, the shared ``ImmutableAuditLog``, ``ml.validation`` and ``ml.provenance`` — it adds
**no new model architecture** and creates **no parallel systems**. It trains/evaluates/
benchmarks/compares/scores models; it does not serve, persist, secure, deploy, or modify
Track 1. Boundary: imports ``ml`` + sibling ``backend`` only; never ``frontend``.
"""

from __future__ import annotations

from .version import (
    DEFAULT_SEED, DETERMINISTIC_EPOCH, FINGERPRINT_DECIMALS, REAL_MODEL_TRAINING_VERSION,
    TRAINING_AUDIT_VERSION, TRAINING_BENCHMARK_VERSION, TRAINING_COMPARISON_VERSION,
    TRAINING_DATASET_VERSION, TRAINING_DOMAIN_VERSION, TRAINING_EVALUATION_VERSION,
    TRAINING_EXPERIMENT_VERSION, TRAINING_FEATURE_VERSION, TRAINING_IDENTITY_VERSION,
    TRAINING_LINEAGE_VERSION, TRAINING_READINESS_VERSION, TRAINING_REGISTRY_VERSION,
    TRAINING_REPORT_VERSION, TRAINING_RUN_VERSION, TRAINING_WINDOW_VERSION,
)
from .models import (
    Architecture, BenchmarkSummaryRecord, CandidateModelRecord, ComparisonRecord, EntityKind,
    EvaluationSummaryRecord, ModelStatus, ReadinessDimension, RealTrainingDatasetRecord,
    ServingReadinessClass, ServingReadinessRecord, SplitStrategy, TrainingAuditRecord,
    TrainingExperimentRecord, TrainingRegistryRecord, TrainingValidationRecord, WindowingSpec,
)
from .data import RecordingInput, DatasetBuildError, build_real_training_dataset
from .training import TrainOutput, train_architecture
from .benchmarking import benchmark
from .evaluation import evaluate_model
from .comparison import compare
from .experiments import build_experiment
from .readiness import ServingReadinessEngine
from .validation import TrainingContentValidator
from .registry import RealModelRegistry, RegistryError
from .audit import AuditError, ImmutableAuditLog, make_training_audit_log
from .schemas import ENTITY_CONTRACTS, validate_entity
from .service import (
    ALL_ARCHITECTURES, PreparedDataset, RealModelTrainingError, RealModelTrainingService,
    TrainingProgramOutcome,
)

__all__ = [
    # versions
    "REAL_MODEL_TRAINING_VERSION", "TRAINING_DOMAIN_VERSION", "TRAINING_IDENTITY_VERSION",
    "TRAINING_DATASET_VERSION", "TRAINING_WINDOW_VERSION", "TRAINING_FEATURE_VERSION",
    "TRAINING_RUN_VERSION", "TRAINING_EXPERIMENT_VERSION", "TRAINING_EVALUATION_VERSION",
    "TRAINING_BENCHMARK_VERSION", "TRAINING_COMPARISON_VERSION", "TRAINING_READINESS_VERSION",
    "TRAINING_REGISTRY_VERSION", "TRAINING_AUDIT_VERSION", "TRAINING_LINEAGE_VERSION",
    "TRAINING_REPORT_VERSION", "DEFAULT_SEED", "DETERMINISTIC_EPOCH", "FINGERPRINT_DECIMALS",
    # domain
    "Architecture", "BenchmarkSummaryRecord", "CandidateModelRecord", "ComparisonRecord",
    "EntityKind", "EvaluationSummaryRecord", "ModelStatus", "ReadinessDimension",
    "RealTrainingDatasetRecord", "ServingReadinessClass", "ServingReadinessRecord",
    "SplitStrategy", "TrainingAuditRecord", "TrainingExperimentRecord", "TrainingRegistryRecord",
    "TrainingValidationRecord", "WindowingSpec",
    # pipeline / engines / infra
    "RecordingInput", "DatasetBuildError", "build_real_training_dataset", "TrainOutput",
    "train_architecture", "benchmark", "evaluate_model", "compare", "build_experiment",
    "ServingReadinessEngine", "TrainingContentValidator", "RealModelRegistry", "RegistryError",
    "AuditError", "ImmutableAuditLog", "make_training_audit_log", "ENTITY_CONTRACTS",
    "validate_entity", "ALL_ARCHITECTURES", "PreparedDataset", "RealModelTrainingError",
    "RealModelTrainingService", "TrainingProgramOutcome",
]
