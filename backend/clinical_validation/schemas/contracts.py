"""Entity contracts for the Clinical Validation domain (DRP6-K; no undocumented objects)."""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    CLINICAL_BENCHMARK_VERSION, CLINICAL_PERFORMANCE_VERSION,
    CLINICAL_RELIABILITY_VERSION, CLINICAL_CALIBRATION_VERSION, CLINICAL_COMPARISON_VERSION,
    CLINICAL_EVIDENCE_VERSION, CLINICAL_READINESS_VERSION, CLINICAL_REGISTRY_VERSION,
    CLINICAL_AUDIT_VERSION, CLINICAL_LINEAGE_VERSION, CLINICAL_VALIDATION_RECORD_VERSION,
    CLINICAL_REPORT_VERSION,
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
        return {"name": self.name, "version": self.version,
                "required_fields": list(self.required_fields),
                "validation_rules": list(self.validation_rules),
                "lineage_rule": self.lineage_rule, "audit_rule": self.audit_rule}


ENTITY_CONTRACTS: dict[str, EntityContract] = {
    "BenchmarkRecord": EntityContract(
        "BenchmarkRecord", CLINICAL_BENCHMARK_VERSION,
        ("benchmark_id", "model_id", "architecture", "dataset_label", "deterministic_metrics",
         "performance", "source_benchmark_id"),
        ("deterministic metrics (acc/prec/rec/f1/roc_auc/pr_auc/sensitivity/specificity/ece/brier)"
         " enter the id + signature",
         "performance (latency/memory/inference/training time) is informational; never hashed",
         "reuses the DRP-2 benchmark; adds sensitivity + specificity"),
        "benchmark node parents the production-model node", "benchmark audited"),
    "PerformanceRecord": EntityContract(
        "PerformanceRecord", CLINICAL_PERFORMANCE_VERSION, ("performance_id", "model_id", "measures"),
        ("informational performance measures; never hashed",), "n/a", "performance audited"),
    "ReliabilityRecord": EntityContract(
        "ReliabilityRecord", CLINICAL_RELIABILITY_VERSION,
        ("reliability_id", "model_id", "repeatable", "reproducible", "cross_run_stability",
         "cross_dataset_stability", "failure_modes", "reliability_score"),
        ("repeatability/reproducibility/cross-run/cross-dataset stability + failure modes",
         "deterministic; structured outputs"),
        "n/a", "reliability audited"),
    "CalibrationRecord": EntityContract(
        "CalibrationRecord", CLINICAL_CALIBRATION_VERSION,
        ("calibration_id", "model_id", "expected_calibration_error", "brier", "quality",
         "confidence_distribution", "reliability_curve"),
        ("ECE + Brier + quality band + confidence distribution + reliability curve",
         "deterministic; traceable; versioned"),
        "n/a", "calibration audited"),
    "ComparisonRecord": EntityContract(
        "ComparisonRecord", CLINICAL_COMPARISON_VERSION,
        ("comparison_id", "n_models", "metrics", "ranking", "recommended_model"),
        ("objective ranking + best-per-metric; deterministic (model_id tiebreak)",),
        "n/a", "comparison audited"),
    "EvidenceRecord": EntityContract(
        "EvidenceRecord", CLINICAL_EVIDENCE_VERSION,
        ("evidence_id", "model_id", "benchmark_id", "performance_id", "reliability_id",
         "calibration_id", "evidence_kinds", "fingerprint"),
        ("binds benchmark + performance + reliability + calibration under one fingerprint",),
        "evidence node parents the evaluation node", "evidence audited"),
    "ReadinessRecord": EntityContract(
        "ReadinessRecord", CLINICAL_READINESS_VERSION,
        ("readiness_id", "target_id", "score", "classification", "dimensions"),
        ("seven dimensions (benchmark/reliability/calibration/evidence/registry/audit/lineage)",
         "READY requires all present"),
        "readiness node parents the evidence node", "readiness audited"),
    "ClinicalValidationRecord": EntityContract(
        "ClinicalValidationRecord", CLINICAL_VALIDATION_RECORD_VERSION,
        ("identity", "model_id", "architecture", "dataset_label", "benchmark_id", "performance_id",
         "reliability_id", "calibration_id", "evidence_id", "readiness_id", "status", "version"),
        ("immutable (frozen) once validated",
         "binds benchmark + performance + reliability + calibration + evidence + readiness"),
        "validation references the readiness node (Dataset -> ... -> Readiness)",
        "every validation event audited"),
    "ValidationRegistryRecord": EntityContract(
        "ValidationRegistryRecord", CLINICAL_REGISTRY_VERSION,
        ("validation_id", "model_id", "benchmark_id", "evidence_id", "readiness_id", "status",
         "version", "lineage_id"),
        ("no evidence exists outside the registry; no orphans; silent overwrite forbidden",),
        "lineage_id references the readiness node", "registry changes audited"),
    "ValidationAuditRecord": EntityContract(
        "ValidationAuditRecord", CLINICAL_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",),
        "n/a", "immutable; append-only; tamper-evident (shared ImmutableAuditLog)"),
    "ValidationLineageRecord": EntityContract(
        "ValidationLineageRecord", CLINICAL_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "parents reference the upstream lineage node", "lineage event audited"),
    "ClinicalValidationReport": EntityContract(
        "ClinicalValidationReport", CLINICAL_REPORT_VERSION,
        ("report_type", "clinical_report_version"),
        ("deterministic; reproducible for a given record/registry state",), "n/a", "n/a"),
}


def contract_for(name: str) -> EntityContract:
    if name not in ENTITY_CONTRACTS:
        raise KeyError(f"no contract for entity {name!r}")
    return ENTITY_CONTRACTS[name]


def validate_entity(name: str, entity_dict: dict) -> tuple[bool, list]:
    contract = contract_for(name)
    missing = [f for f in contract.required_fields
               if f not in entity_dict or entity_dict[f] in (None, "")]
    return (len(missing) == 0), missing


__all__ = ["EntityContract", "ENTITY_CONTRACTS", "contract_for", "validate_entity"]
