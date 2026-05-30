"""Entity contracts for the Clinical Inference domain (no undocumented objects).

For each entity: Schema (required fields) · Validation Rules · Lineage Rule · Audit
Rule. ``validate_entity`` checks an entity's serialized form against its schema.
Mirrors ``backend.model_foundation.schemas.contracts``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    INFERENCE_DOMAIN_VERSION, INFERENCE_IDENTITY_VERSION, INFERENCE_PREDICTION_VERSION,
    INFERENCE_CONFIDENCE_VERSION, INFERENCE_CALIBRATION_VERSION, INFERENCE_EXPLAINABILITY_VERSION,
    INFERENCE_REGISTRY_VERSION, INFERENCE_AUDIT_VERSION, INFERENCE_LINEAGE_VERSION,
    INFERENCE_VALIDATION_VERSION, INFERENCE_REPORT_VERSION,
)


@dataclass(frozen=True)
class EntityContract:
    name: str
    version: str
    required_fields: tuple[str, ...]
    validation_rules: tuple[str, ...]
    lineage_rule: str
    audit_rule: str

    def to_dict(self) -> dict:
        return {
            "name": self.name, "version": self.version,
            "required_fields": list(self.required_fields),
            "validation_rules": list(self.validation_rules),
            "lineage_rule": self.lineage_rule, "audit_rule": self.audit_rule,
        }


ENTITY_CONTRACTS: dict[str, EntityContract] = {
    "InferenceIdentity": EntityContract(
        "InferenceIdentity", INFERENCE_IDENTITY_VERSION,
        ("prediction_id", "model_id", "feature_asset_id"),
        ("prediction_id matches /^prediction\\+[0-9a-f]{16}$/", "content-addressed from model + input"),
        "derived_from = model_id", "minted-once; never modified"),
    "PredictionRecord": EntityContract(
        "PredictionRecord", INFERENCE_PREDICTION_VERSION,
        ("predicted_class", "predicted_label", "classes", "scores"),
        ("class probabilities sum to 1 + finite", "predicted_class = argmax", "reproducible"),
        "n/a", "prediction generation audited"),
    "PredictionClass": EntityContract(
        "PredictionClass", INFERENCE_DOMAIN_VERSION, ("class_index", "class_label", "probability"),
        ("0 <= probability <= 1",), "n/a", "n/a"),
    "PredictionScore": EntityContract(
        "PredictionScore", INFERENCE_DOMAIN_VERSION, ("name", "value"), (), "n/a", "n/a"),
    "ConfidenceRecord": EntityContract(
        "ConfidenceRecord", INFERENCE_CONFIDENCE_VERSION,
        ("confidence_score", "confidence_interval", "prediction_stability",
         "prediction_reliability", "confidence_level"),
        ("all scores in [0,1]", "confidence_level is a closed ConfidenceLevel", "deterministic"),
        "n/a", "confidence assessment audited"),
    "CalibrationRecord": EntityContract(
        "CalibrationRecord", INFERENCE_CALIBRATION_VERSION,
        ("expected_calibration_error", "brier_score", "reliability_assessment",
         "calibration_quality", "reference_n_samples"),
        ("ECE in [0,1]", "calibration_quality is a closed CalibrationQuality", "deterministic"),
        "n/a", "calibration assessment audited"),
    "ExplanationRecord": EntityContract(
        "ExplanationRecord", INFERENCE_EXPLAINABILITY_VERSION,
        ("method", "feature_contributions", "feature_importance", "decision_factors"),
        ("structured outputs only (no images/UI)", "method is a closed ExplanationMethod",
         "feature_importance normalized"),
        "n/a", "explanation generation audited"),
    "InferenceValidationRecord": EntityContract(
        "InferenceValidationRecord", INFERENCE_VALIDATION_VERSION, ("validation_id", "ok", "checks"),
        ("content checks: prediction/confidence/calibration/explanation/determinism",
         "structured (name, passed, detail); never exceptions"),
        "n/a", "validation recorded in the audit trail"),
    "InferenceRegistryRecord": EntityContract(
        "InferenceRegistryRecord", INFERENCE_REGISTRY_VERSION,
        ("prediction_id", "model_id", "feature_asset_id", "status", "version", "lineage_id"),
        ("no prediction asset exists outside the registry",
         "silent overwrite with different content forbidden"),
        "lineage_id references the prediction lineage node", "registry changes audited"),
    "InferenceAuditRecord": EntityContract(
        "InferenceAuditRecord", INFERENCE_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",
         "prev_hash links to the previous event (chain)"),
        "n/a", "immutable; append-only; tamper-evident (shared ImmutableAuditLog)"),
    "InferenceLineageRecord": EntityContract(
        "InferenceLineageRecord", INFERENCE_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "parents reference the model node + the input feature node", "lineage event audited"),
    "InferenceRecord": EntityContract(
        "InferenceRecord", INFERENCE_DOMAIN_VERSION,
        ("identity", "model_id", "feature_asset_id", "case_id", "patient_id", "prediction",
         "confidence", "calibration", "explanation", "validation", "status", "version"),
        ("immutable (frozen) once generated", "carries no model weights/raw signal",
         "derived from a verified model + a validated feature asset"),
        "prediction node parents the model node + the input feature node "
        "(Patient -> ... -> Model -> Prediction)",
        "every execution/prediction/confidence/calibration/explanation/version/registration "
        "event audited"),
    "InferenceReport": EntityContract(
        "InferenceReport", INFERENCE_REPORT_VERSION, ("report_type", "inference_report_version"),
        ("deterministic; reproducible for a given asset/registry state",), "n/a", "n/a"),
}


def contract_for(name: str) -> EntityContract:
    if name not in ENTITY_CONTRACTS:
        raise KeyError(f"no contract for entity {name!r}")
    return ENTITY_CONTRACTS[name]


def validate_entity(name: str, entity_dict: dict) -> tuple[bool, list]:
    """Check an entity's serialized form against its contract's required fields."""
    contract = contract_for(name)
    missing = [f for f in contract.required_fields
               if f not in entity_dict or entity_dict[f] in (None, "")]
    return (len(missing) == 0), missing
