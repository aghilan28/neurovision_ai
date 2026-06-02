"""``backend/production_models`` — Production Model Program (DRP-2).

Transforms the platform's **reference-grade** models into **production-candidate models**
with objective evaluation, benchmark, and readiness evidence. The scope is *model
development and validation* and nothing else:

    build dataset (from feature assets) -> train (deterministic, reproducible) ->
    track experiment -> evaluate -> benchmark -> compare -> score readiness ->
    validate -> register -> track + audit + trace

No model serving, no APIs, no frontend/backend-API/operations/deployment/security changes,
no inference-architecture changes (all out of scope for this phase).

Built strictly on the existing platform: it **reuses** the model-foundation dataset
builder + base evaluator + reference architectures, the shared ``ml.lineage`` tracker, the
shared ``ImmutableAuditLog``, ``ml.validation``, and the shared ``DatasetRegistry`` +
``ModelRegistry`` (integration, not duplication — **no parallel registries**). The four
reference architectures are wrapped (never removed); a deterministic ``HYBRID_EEG``
architecture is added. A production model's readiness lineage parents the benchmark, which
parents the model + evaluation, which parent the training experiment + run, which parent
the dataset + feature assets — so a single ``verify_chain`` proves

    Patient -> Case -> EEG -> Processed -> Feature -> Dataset -> Training Run ->
    Training Experiment -> Model -> Benchmark -> Readiness Assessment.

Boundary (NR-8): part of the ``backend`` Application layer. Imports ``ml`` + sibling
``backend`` only; never ``frontend``. Models are deterministic pure-NumPy (no serving).
Tests live in the repository-root ``tests/`` (``tests/test_production_models*.py``).
"""

from __future__ import annotations

from .version import (
    PRODUCTION_MODELS_VERSION, PRODUCTION_DOMAIN_VERSION, PRODUCTION_IDENTITY_VERSION,
    PRODUCTION_ARCH_VERSION, PRODUCTION_TRAINING_VERSION, PRODUCTION_BENCHMARK_VERSION,
    PRODUCTION_EVALUATION_VERSION, PRODUCTION_READINESS_VERSION, PRODUCTION_REGISTRY_VERSION,
    PRODUCTION_AUDIT_VERSION, PRODUCTION_LINEAGE_VERSION, PRODUCTION_VALIDATION_VERSION,
    PRODUCTION_REPORT_VERSION, DEFAULT_SEED,
)
from .models import (
    ProductionArchitecture, ModelStatus, ExperimentStatus, ReadinessClass, ReadinessDimension,
    EntityKind, ProductionModelIdentity, ModelVersion, BenchmarkVersion, TrainingExperimentRecord,
    ModelBenchmarkRecord, ModelEvaluationRecord, ModelReadinessRecord, ModelValidationRecord,
    ModelAuditRecord, ModelLineageRecord, ModelRegistryRecord, ProductionModelRecord,
)
from .identity import (
    Identity, IdentityError, mint_identity, parse_identity, validate_identity,
)
from .architectures import (
    HybridModel, ReferenceArchitectureWrapper, REFERENCE_OF, PRODUCTION_ARCHITECTURES,
    ArchitectureError, architecture_catalog, build_production_model,
)
from .training import (
    HYPERPARAMETER_REGISTRY, TrainingConfig, TrainingError, TrainingResult, train_production,
)
from .benchmarking import benchmark_model
from .evaluation import build_model_evaluation, compare_models
from .readiness import ReadinessEngine
from .registry import ProductionModelRegistry, RegistryError
from .audit import make_production_audit_log, ImmutableAuditLog, AuditError
from .lineage import (
    make_training_experiment_lineage, make_production_model_lineage, make_benchmark_lineage,
    make_readiness_lineage,
)
from .validation import ProductionModelContentValidator, ProductionModelIntegrityValidator
from .schemas import ENTITY_CONTRACTS, validate_entity
from .service import ProductionModelService, ProductionModelOutcome, ProductionModelError

__all__ = [
    # versions
    "PRODUCTION_MODELS_VERSION", "PRODUCTION_DOMAIN_VERSION", "PRODUCTION_IDENTITY_VERSION",
    "PRODUCTION_ARCH_VERSION", "PRODUCTION_TRAINING_VERSION", "PRODUCTION_BENCHMARK_VERSION",
    "PRODUCTION_EVALUATION_VERSION", "PRODUCTION_READINESS_VERSION", "PRODUCTION_REGISTRY_VERSION",
    "PRODUCTION_AUDIT_VERSION", "PRODUCTION_LINEAGE_VERSION", "PRODUCTION_VALIDATION_VERSION",
    "PRODUCTION_REPORT_VERSION", "DEFAULT_SEED",
    # models / vocab
    "ProductionArchitecture", "ModelStatus", "ExperimentStatus", "ReadinessClass",
    "ReadinessDimension", "EntityKind", "ProductionModelIdentity", "ModelVersion",
    "BenchmarkVersion", "TrainingExperimentRecord", "ModelBenchmarkRecord", "ModelEvaluationRecord",
    "ModelReadinessRecord", "ModelValidationRecord", "ModelAuditRecord", "ModelLineageRecord",
    "ModelRegistryRecord", "ProductionModelRecord",
    # identity
    "Identity", "IdentityError", "mint_identity", "parse_identity", "validate_identity",
    # architectures
    "HybridModel", "ReferenceArchitectureWrapper", "REFERENCE_OF", "PRODUCTION_ARCHITECTURES",
    "ArchitectureError", "architecture_catalog", "build_production_model",
    # training / benchmarking / evaluation / readiness
    "HYPERPARAMETER_REGISTRY", "TrainingConfig", "TrainingError", "TrainingResult",
    "train_production", "benchmark_model", "build_model_evaluation", "compare_models",
    "ReadinessEngine",
    # registry / audit / lineage / validation / schemas
    "ProductionModelRegistry", "RegistryError", "make_production_audit_log", "ImmutableAuditLog",
    "AuditError", "make_training_experiment_lineage", "make_production_model_lineage",
    "make_benchmark_lineage", "make_readiness_lineage", "ProductionModelContentValidator",
    "ProductionModelIntegrityValidator", "ENTITY_CONTRACTS", "validate_entity",
    # service
    "ProductionModelService", "ProductionModelOutcome", "ProductionModelError",
]
