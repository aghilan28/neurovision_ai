"""``backend/inference_foundation`` — Clinical Inference Foundation (Productization P5).

Transforms a trained model (P4) + a feature asset (P3) into a **validated prediction
asset**. The scope is inference and nothing else:

    load + verify model -> execute -> predict -> confidence -> calibration ->
    explanation -> validate -> register -> track + audit + trace

No APIs, serving, deployment, frontend, user accounts, or serving infrastructure (all
out of scope for this phase).

Built strictly on P1-P4: it reuses the existing EEG / processed-EEG / feature / dataset
/ training / evaluation / model artifacts; it never redesigns prior phases or creates
parallel pipelines. A prediction's lineage parents the model node + the input feature
node, so the platform-wide chain is
Patient -> Case -> EEG -> Processed -> Feature -> Dataset -> Training Run -> Model -> Prediction.

Boundary (NR-8): part of the ``backend`` Application layer. Imports ``ml``
(provenance/lineage/validation), reuses the P4 training/dataset/metrics modules (for
deterministic model reconstruction + calibration), and reuses the platform's
tamper-evident audit log from ``backend.clinical_cases.audit`` (intra-backend reuse — no
parallel audit or lineage systems). It never imports ``frontend``.

Tests live in the repository-root ``tests/`` (``tests/test_inference_foundation*.py``)
and reuse the P1-P4 assets + P1 EEG fixtures; design notes live in ``docs/``.
"""

from __future__ import annotations

from .version import (
    INFERENCE_FOUNDATION_VERSION, INFERENCE_DOMAIN_VERSION, INFERENCE_IDENTITY_VERSION,
    INFERENCE_EXECUTION_VERSION, INFERENCE_PREDICTION_VERSION, INFERENCE_CONFIDENCE_VERSION,
    INFERENCE_CALIBRATION_VERSION, INFERENCE_EXPLAINABILITY_VERSION, INFERENCE_REGISTRY_VERSION,
    INFERENCE_AUDIT_VERSION, INFERENCE_LINEAGE_VERSION, INFERENCE_VALIDATION_VERSION,
    INFERENCE_REPORT_VERSION,
)
from .models import (
    ConfidenceLevel, CalibrationQuality, ExplanationMethod, InferenceStatus, InferenceIdentity,
    PredictionClass, PredictionScore, PredictionRecord, ConfidenceRecord, CalibrationRecord,
    FeatureContribution, ExplanationRecord, InferenceValidationRecord, InferenceAuditRecord,
    InferenceLineageRecord, PredictionVersion, InferenceRegistryRecord, InferenceRecord,
)
from .identity import (
    Identity, mint_identity, validate_identity, parse_identity, IdentityError,
)
from .inference import ModelExecutionEngine, ModelExecutionError, PredictionEngine, PredictionError
from .confidence import ConfidenceEngine
from .calibration import CalibrationEngine
from .explainability import ExplainabilityEngine
from .registry import InferenceRegistry
from .audit import make_inference_audit_log, ImmutableAuditLog, AuditError
from .lineage import (
    make_prediction_lineage, inference_version_bundle, LineageTracker, LineageRecord,
)
from .validation import InferenceContentValidator, InferenceIntegrityValidator
from .service import InferenceFoundationService, InferenceOutcome, InferenceFoundationError

__all__ = [
    # versions
    "INFERENCE_FOUNDATION_VERSION", "INFERENCE_DOMAIN_VERSION", "INFERENCE_IDENTITY_VERSION",
    "INFERENCE_EXECUTION_VERSION", "INFERENCE_PREDICTION_VERSION", "INFERENCE_CONFIDENCE_VERSION",
    "INFERENCE_CALIBRATION_VERSION", "INFERENCE_EXPLAINABILITY_VERSION", "INFERENCE_REGISTRY_VERSION",
    "INFERENCE_AUDIT_VERSION", "INFERENCE_LINEAGE_VERSION", "INFERENCE_VALIDATION_VERSION",
    "INFERENCE_REPORT_VERSION",
    # models / vocab
    "ConfidenceLevel", "CalibrationQuality", "ExplanationMethod", "InferenceStatus",
    "InferenceIdentity", "PredictionClass", "PredictionScore", "PredictionRecord", "ConfidenceRecord",
    "CalibrationRecord", "FeatureContribution", "ExplanationRecord", "InferenceValidationRecord",
    "InferenceAuditRecord", "InferenceLineageRecord", "PredictionVersion", "InferenceRegistryRecord",
    "InferenceRecord",
    # identity
    "Identity", "mint_identity", "validate_identity", "parse_identity", "IdentityError",
    # engines
    "ModelExecutionEngine", "ModelExecutionError", "PredictionEngine", "PredictionError",
    "ConfidenceEngine", "CalibrationEngine", "ExplainabilityEngine",
    # registry / audit / lineage / validation
    "InferenceRegistry", "make_inference_audit_log", "ImmutableAuditLog", "AuditError",
    "make_prediction_lineage", "inference_version_bundle", "LineageTracker", "LineageRecord",
    "InferenceContentValidator", "InferenceIntegrityValidator",
    # service
    "InferenceFoundationService", "InferenceOutcome", "InferenceFoundationError",
]
