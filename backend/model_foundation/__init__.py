"""``backend/model_foundation`` — Model Foundation Platform (Productization P4).

Transforms feature assets (from Productization P3) into **validated trained models**.
The scope is model creation and nothing else:

    build dataset (from feature assets / external manifests) -> train -> evaluate ->
    track experiment -> validate -> register model -> track + audit + trace

No production inference, serving, APIs, user predictions, or frontend integration
(all out of scope for this phase).

Built strictly on P1 + P2 + P3: it reuses the existing EEG, processed-EEG, and feature
assets; it never redesigns prior phases or creates parallel EEG pipelines. A model's
lineage parents the training run, which parents the dataset, which parents the feature
assets — so the platform-wide chain is
Patient -> Case -> EEG -> Processed -> Feature -> Dataset -> Training Run -> Model.

Boundary (NR-8): part of the ``backend`` Application layer. Imports ``ml``
(provenance/lineage/validation) and reuses the platform's tamper-evident audit log
from ``backend.clinical_cases.audit`` (intra-backend reuse — no parallel audit or
lineage systems). It never imports ``frontend``. Models are deterministic pure-NumPy
reference baselines (no deep-learning framework, no serving).

Tests live in the repository-root ``tests/`` (``tests/test_model_foundation*.py``) and
reuse the P1/P2/P3 assets + P1 EEG fixtures; design notes live in ``docs/``.
"""

from __future__ import annotations

from .version import (
    MODEL_FOUNDATION_VERSION, MODEL_DOMAIN_VERSION, MODEL_IDENTITY_VERSION, MODEL_DATASET_VERSION,
    MODEL_TRAINING_VERSION, MODEL_EVALUATION_VERSION, MODEL_EXPERIMENT_VERSION, MODEL_ARCH_VERSION,
    MODEL_REGISTRY_VERSION, MODEL_AUDIT_VERSION, MODEL_LINEAGE_VERSION, MODEL_VALIDATION_VERSION,
    MODEL_REPORT_VERSION, DEFAULT_SEED,
)
from .models import (
    ModelArchitecture, DatasetSource, SplitName, DatasetStatus, ModelStatus, ExperimentStatus,
    ModelIdentity, DataSplit, DatasetRecord, TrainingRunRecord, EvaluationRecord, ExperimentRecord,
    ModelMetadata, ModelValidationRecord, ModelAuditRecord, ModelLineageRecord, ModelVersion,
    ModelRegistryRecord, ModelRecord,
)
from .identity import (
    Identity, mint_identity, validate_identity, parse_identity, IdentityError,
)
from .datasets import (
    ExternalDatasetConnector, DatasetConnectorError, CONNECTOR_SPECS, DatasetBundle,
    DatasetBuildError, build_feature_dataset, assemble_feature_vector, default_label_fn,
    patient_disjoint_split, ASSEMBLY_FEATURE_VECTORS,
)
from .training import BaselineModel, build_model, train, TrainingError
from .evaluation import evaluate, metrics
from .experiments import build_experiment, ExperimentRegistry
from .registry import DatasetRegistry, ModelRegistry
from .audit import make_model_audit_log, ImmutableAuditLog, AuditError
from .lineage import (
    make_dataset_lineage, make_training_lineage, make_evaluation_lineage, make_model_lineage,
    model_version_bundle, LineageTracker, LineageRecord,
)
from .validation import ModelContentValidator, ModelIntegrityValidator
from .service import ModelFoundationService, ModelOutcome, ModelFoundationError

__all__ = [
    # versions
    "MODEL_FOUNDATION_VERSION", "MODEL_DOMAIN_VERSION", "MODEL_IDENTITY_VERSION", "MODEL_DATASET_VERSION",
    "MODEL_TRAINING_VERSION", "MODEL_EVALUATION_VERSION", "MODEL_EXPERIMENT_VERSION", "MODEL_ARCH_VERSION",
    "MODEL_REGISTRY_VERSION", "MODEL_AUDIT_VERSION", "MODEL_LINEAGE_VERSION", "MODEL_VALIDATION_VERSION",
    "MODEL_REPORT_VERSION", "DEFAULT_SEED",
    # models / vocab
    "ModelArchitecture", "DatasetSource", "SplitName", "DatasetStatus", "ModelStatus",
    "ExperimentStatus", "ModelIdentity", "DataSplit", "DatasetRecord", "TrainingRunRecord",
    "EvaluationRecord", "ExperimentRecord", "ModelMetadata", "ModelValidationRecord",
    "ModelAuditRecord", "ModelLineageRecord", "ModelVersion", "ModelRegistryRecord", "ModelRecord",
    # identity
    "Identity", "mint_identity", "validate_identity", "parse_identity", "IdentityError",
    # datasets
    "ExternalDatasetConnector", "DatasetConnectorError", "CONNECTOR_SPECS", "DatasetBundle",
    "DatasetBuildError", "build_feature_dataset", "assemble_feature_vector", "default_label_fn",
    "patient_disjoint_split", "ASSEMBLY_FEATURE_VECTORS",
    # training / evaluation / experiments
    "BaselineModel", "build_model", "train", "TrainingError", "evaluate", "metrics",
    "build_experiment", "ExperimentRegistry",
    # registry / audit / lineage / validation
    "DatasetRegistry", "ModelRegistry", "make_model_audit_log", "ImmutableAuditLog", "AuditError",
    "make_dataset_lineage", "make_training_lineage", "make_evaluation_lineage", "make_model_lineage",
    "model_version_bundle", "LineageTracker", "LineageRecord",
    "ModelContentValidator", "ModelIntegrityValidator",
    # service
    "ModelFoundationService", "ModelOutcome", "ModelFoundationError",
]
