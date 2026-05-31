"""Entity contracts for the Production Model domain (DRP2-K; no undocumented objects).

For each entity: Schema (required fields) · Validation Rules · Lineage Rule · Audit Rule.
``validate_entity`` checks an entity's serialized form against its schema. Mirrors
``backend.model_foundation.schemas.contracts``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    PRODUCTION_DOMAIN_VERSION, PRODUCTION_IDENTITY_VERSION, PRODUCTION_TRAINING_VERSION,
    PRODUCTION_BENCHMARK_VERSION, PRODUCTION_EVALUATION_VERSION, PRODUCTION_READINESS_VERSION,
    PRODUCTION_REGISTRY_VERSION, PRODUCTION_AUDIT_VERSION, PRODUCTION_LINEAGE_VERSION,
    PRODUCTION_VALIDATION_VERSION, PRODUCTION_REPORT_VERSION,
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
    "ProductionModelIdentity": EntityContract(
        "ProductionModelIdentity", PRODUCTION_IDENTITY_VERSION,
        ("model_id", "training_run_id", "training_experiment_id", "architecture"),
        ("model_id matches /^production_model\\+[0-9a-f]{16}$/",
         "content-addressed from the training run"),
        "derived_from = training_run_id", "minted-once; never modified"),
    "TrainingExperimentRecord": EntityContract(
        "TrainingExperimentRecord", PRODUCTION_TRAINING_VERSION,
        ("experiment_id", "architecture", "dataset_id", "training_run_id", "seed",
         "params_fingerprint", "reproducible"),
        ("deterministic (seeded) + reproducibility verified by re-training",
         "tracks hyperparameters + metrics + history"),
        "training-experiment node parents the training-run node", "training audited"),
    "ModelBenchmarkRecord": EntityContract(
        "ModelBenchmarkRecord", PRODUCTION_BENCHMARK_VERSION,
        ("benchmark_id", "model_id", "architecture", "dataset_id", "split",
         "deterministic_metrics", "performance"),
        ("deterministic metrics (accuracy/precision/recall/f1/roc_auc/pr_auc/ece/brier) "
         "enter the id + signature",
         "performance (latency/memory/training-time/inference-time) is informational; "
         "never hashed"),
        "benchmark node parents the model node + the evaluation node", "benchmark audited"),
    "ModelEvaluationRecord": EntityContract(
        "ModelEvaluationRecord", PRODUCTION_EVALUATION_VERSION,
        ("model_evaluation_id", "model_id", "evaluation_id", "dataset_id", "confusion_matrix"),
        ("structured deterministic analyses: confusion/calibration/error/class-distribution/"
         "stability/reliability", "references the base model-foundation evaluation"),
        "references the evaluation lineage node", "evaluation audited"),
    "ModelReadinessRecord": EntityContract(
        "ModelReadinessRecord", PRODUCTION_READINESS_VERSION,
        ("readiness_id", "model_id", "score", "classification", "dimensions"),
        ("seven dimensions (training/evaluation/benchmark/registry/validation/lineage/audit)",
         "READY requires all present + validation passes"),
        "readiness node parents the benchmark node", "readiness audited"),
    "ModelValidationRecord": EntityContract(
        "ModelValidationRecord", PRODUCTION_VALIDATION_VERSION, ("validation_id", "ok", "checks"),
        ("content checks: architecture/training/benchmark/evaluation/determinism",
         "structured (name, passed, detail); never exceptions"),
        "n/a", "validation recorded in the audit trail"),
    "ModelRegistryRecord": EntityContract(
        "ModelRegistryRecord", PRODUCTION_REGISTRY_VERSION,
        ("model_id", "architecture", "dataset_id", "training_experiment_id", "benchmark_id",
         "model_evaluation_id", "readiness_id", "status", "version", "lineage_id"),
        ("no model exists outside the registry; no orphans",
         "cross-references the shared dataset + base-model ids; silent overwrite forbidden"),
        "lineage_id references the production-model lineage node", "registry changes audited"),
    "ModelAuditRecord": EntityContract(
        "ModelAuditRecord", PRODUCTION_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",
         "prev_hash links to the previous event (chain)"),
        "n/a", "immutable; append-only; tamper-evident (shared ImmutableAuditLog)"),
    "ModelLineageRecord": EntityContract(
        "ModelLineageRecord", PRODUCTION_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "parents reference the upstream lineage node", "lineage event audited"),
    "ProductionModelRecord": EntityContract(
        "ProductionModelRecord", PRODUCTION_DOMAIN_VERSION,
        ("identity", "architecture", "dataset_id", "training_experiment_id", "benchmark_id",
         "model_evaluation_id", "readiness_id", "validation", "params_fingerprint", "status",
         "version"),
        ("immutable (frozen) once developed", "carries the parameter fingerprint, not raw weights",
         "binds training + benchmark + evaluation + readiness"),
        "model node parents the training-experiment node "
        "(Dataset -> ... -> Model -> Benchmark -> Readiness)",
        "every training/benchmark/evaluation/readiness/version/registration event audited"),
    "ProductionModelReport": EntityContract(
        "ProductionModelReport", PRODUCTION_REPORT_VERSION,
        ("report_type", "production_report_version"),
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


__all__ = ["EntityContract", "ENTITY_CONTRACTS", "contract_for", "validate_entity"]
