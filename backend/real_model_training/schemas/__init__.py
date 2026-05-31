"""``backend/real_model_training/schemas`` — entity contracts (Track 2).

A documented contract per entity (no undocumented objects). ``validate_entity`` checks a
serialized entity against its contract's required fields.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    TRAINING_BENCHMARK_VERSION, TRAINING_COMPARISON_VERSION, TRAINING_DATASET_VERSION,
    TRAINING_DOMAIN_VERSION, TRAINING_EVALUATION_VERSION, TRAINING_EXPERIMENT_VERSION,
    TRAINING_READINESS_VERSION, TRAINING_REGISTRY_VERSION,
)


@dataclass(frozen=True)
class EntityContract:
    name: str
    version: str
    required_fields: tuple
    rules: tuple

    def to_dict(self) -> dict:
        return {"name": self.name, "version": self.version,
                "required_fields": list(self.required_fields), "rules": list(self.rules)}


ENTITY_CONTRACTS: dict = {
    "RealTrainingDatasetRecord": EntityContract(
        "RealTrainingDatasetRecord", TRAINING_DATASET_VERSION,
        ("dataset_id", "source_dataset_id", "n_windows", "class_distribution", "feature_names"),
        ("windowed from real recordings (no synthetic data)",
         "labels derived from real seizure intervals", "split is patient-disjoint or stratified")),
    "TrainingExperimentRecord": EntityContract(
        "TrainingExperimentRecord", TRAINING_EXPERIMENT_VERSION,
        ("experiment_id", "architecture", "dataset_id", "training_run_id", "model_id"),
        ("reproducible training", "tracks dataset/feature/config/hyperparameters + metrics")),
    "EvaluationSummaryRecord": EntityContract(
        "EvaluationSummaryRecord", TRAINING_EVALUATION_VERSION,
        ("evaluation_id", "model_id", "metrics", "confusion_matrix"),
        ("metrics include sensitivity + specificity", "real EEG data only")),
    "BenchmarkSummaryRecord": EntityContract(
        "BenchmarkSummaryRecord", TRAINING_BENCHMARK_VERSION,
        ("benchmark_id", "model_id", "deterministic_metrics", "performance"),
        ("deterministic metrics hashed; performance timings informational (never hashed)",)),
    "ComparisonRecord": EntityContract(
        "ComparisonRecord", TRAINING_COMPARISON_VERSION,
        ("comparison_id", "dataset_id", "ranking", "recommended_model"),
        ("deterministic ranking; ties broken by model id",)),
    "ServingReadinessRecord": EntityContract(
        "ServingReadinessRecord", TRAINING_READINESS_VERSION,
        ("readiness_id", "model_id", "score", "classification", "dimensions"),
        ("classification in NOT_READY/PARTIALLY_READY/READY_FOR_SERVING",
         "READY_FOR_SERVING requires complete evidence + validation_ok")),
    "CandidateModelRecord": EntityContract(
        "CandidateModelRecord", TRAINING_DOMAIN_VERSION,
        ("model_id", "architecture", "dataset_id", "training_run_id", "readiness_class"),
        ("carries a params fingerprint, not raw weights", "trained on real data")),
    "TrainingRegistryRecord": EntityContract(
        "TrainingRegistryRecord", TRAINING_REGISTRY_VERSION,
        ("entity_kind", "entity_id", "version", "lineage_id", "audit_state"),
        ("no orphan records (audit head + lineage node required)",)),
}


def contract_for(name: str) -> EntityContract:
    if name not in ENTITY_CONTRACTS:
        raise KeyError(f"no contract for entity {name!r}")
    return ENTITY_CONTRACTS[name]


def validate_entity(name: str, entity_dict: dict) -> tuple:
    contract = contract_for(name)
    missing = [f for f in contract.required_fields
               if f not in entity_dict or entity_dict[f] in (None, "")]
    return (len(missing) == 0), missing


__all__ = ["EntityContract", "ENTITY_CONTRACTS", "contract_for", "validate_entity"]
