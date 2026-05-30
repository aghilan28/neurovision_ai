"""Entity contracts for the Model Foundation domain (no undocumented objects).

For each entity: Schema (required fields) · Validation Rules · Lineage Rule · Audit
Rule. ``validate_entity`` checks an entity's serialized form against its schema.
Mirrors ``backend.feature_engineering.schemas.contracts``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    MODEL_DOMAIN_VERSION, MODEL_IDENTITY_VERSION, MODEL_DATASET_VERSION, MODEL_TRAINING_VERSION,
    MODEL_EVALUATION_VERSION, MODEL_EXPERIMENT_VERSION, MODEL_REGISTRY_VERSION,
    MODEL_AUDIT_VERSION, MODEL_LINEAGE_VERSION, MODEL_VALIDATION_VERSION, MODEL_REPORT_VERSION,
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
    "ModelIdentity": EntityContract(
        "ModelIdentity", MODEL_IDENTITY_VERSION, ("model_id", "training_run_id", "architecture"),
        ("model_id matches /^model\\+[0-9a-f]{16}$/", "content-addressed from training run"),
        "derived_from = training_run_id", "minted-once; never modified"),
    "DatasetRecord": EntityContract(
        "DatasetRecord", MODEL_DATASET_VERSION,
        ("dataset_id", "source", "name", "n_samples", "n_features", "data_fingerprint", "status"),
        ("source is a closed DatasetSource", "external datasets are manifest-registered (no download)",
         "feature datasets carry a patient-disjoint split + data fingerprint"),
        "dataset node parents the contributing feature-asset nodes", "registration audited"),
    "TrainingRunRecord": EntityContract(
        "TrainingRunRecord", MODEL_TRAINING_VERSION,
        ("training_run_id", "architecture", "dataset_id", "seed", "params_fingerprint"),
        ("deterministic (seeded) + reproducible", "tracks hyperparameters + metrics + history"),
        "training-run node parents the dataset node", "training audited"),
    "EvaluationRecord": EntityContract(
        "EvaluationRecord", MODEL_EVALUATION_VERSION,
        ("evaluation_id", "training_run_id", "dataset_id", "split", "metrics", "confusion_matrix"),
        ("deterministic evaluation only", "accuracy/precision/recall/f1 + calibration + uncertainty"),
        "evaluation node parents the training-run node", "evaluation audited"),
    "ExperimentRecord": EntityContract(
        "ExperimentRecord", MODEL_EXPERIMENT_VERSION,
        ("experiment_id", "name", "dataset_id", "architecture", "training_run_id", "evaluation_id"),
        ("binds dataset + model + config + metrics + artifacts", "every run reproducible"),
        "n/a", "experiment registration audited"),
    "ModelMetadata": EntityContract(
        "ModelMetadata", MODEL_DOMAIN_VERSION,
        ("architecture", "dataset_id", "n_features", "n_classes", "n_params"),
        ("deterministic", "records architecture/seed/hyperparameters + train/eval metrics"),
        "n/a", "n/a"),
    "ModelValidationRecord": EntityContract(
        "ModelValidationRecord", MODEL_VALIDATION_VERSION, ("validation_id", "ok", "checks"),
        ("content checks: dataset/training/evaluation/model/determinism",
         "structured (name, passed, detail); never exceptions"),
        "n/a", "validation recorded in the audit trail"),
    "ModelRegistryRecord": EntityContract(
        "ModelRegistryRecord", MODEL_REGISTRY_VERSION,
        ("model_id", "architecture", "dataset_id", "training_run_id", "status", "version", "lineage_id"),
        ("no model exists outside the registry", "silent overwrite with different content forbidden"),
        "lineage_id references the model lineage node", "registry changes audited"),
    "ModelAuditRecord": EntityContract(
        "ModelAuditRecord", MODEL_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",
         "prev_hash links to the previous event (chain)"),
        "n/a", "immutable; append-only; tamper-evident (shared ImmutableAuditLog)"),
    "ModelLineageRecord": EntityContract(
        "ModelLineageRecord", MODEL_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "parents reference the training-run lineage node", "lineage event audited"),
    "ModelRecord": EntityContract(
        "ModelRecord", MODEL_DOMAIN_VERSION,
        ("identity", "architecture", "dataset_id", "training_run_id", "evaluation_id",
         "experiment_id", "metadata", "validation", "params_fingerprint", "status", "version"),
        ("immutable (frozen) once trained", "carries the parameter fingerprint, not raw weights",
         "derived from a reproducible training run"),
        "model node parents the training-run node (Patient -> ... -> Dataset -> Training Run -> Model)",
        "every dataset/training/evaluation/experiment/version/registration event audited"),
    "ModelReport": EntityContract(
        "ModelReport", MODEL_REPORT_VERSION, ("report_type", "model_report_version"),
        ("deterministic; reproducible for a given record/registry state",), "n/a", "n/a"),
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
