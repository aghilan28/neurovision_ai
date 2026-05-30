"""Entity contracts for the multi-case-intelligence domain.

Each entity declares its Schema · Version · Validation Rules · Version Rules ·
Audit Rules · Lineage Rules in one versioned object (mirrors the convention used
by clinical_cases/findings/knowledge).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    INTEL_COHORT_VERSION, INTEL_ANALYTICS_VERSION, INTEL_TREND_VERSION,
    INTEL_QUALITY_VERSION, INTEL_REPORT_VERSION, INTEL_REGISTRY_VERSION,
    INTEL_AUDIT_VERSION, INTEL_LINEAGE_VERSION,
)


@dataclass(frozen=True)
class EntityContract:
    name: str
    version: str
    required_fields: tuple[str, ...]
    validation_rules: tuple[str, ...]
    version_rule: str
    audit_rule: str
    lineage_rule: str

    def to_dict(self) -> dict:
        return {"name": self.name, "version": self.version,
                "required_fields": list(self.required_fields),
                "validation_rules": list(self.validation_rules),
                "version_rule": self.version_rule, "audit_rule": self.audit_rule,
                "lineage_rule": self.lineage_rule}


ENTITY_CONTRACTS: dict[str, EntityContract] = {
    "Cohort": EntityContract(
        "Cohort", INTEL_COHORT_VERSION, ("cohort_id", "definition", "members"),
        ("cohort_id matches /^cohort\\+[0-9a-f]{16}$/", "members are sorted + unique",
         "logical id derives from the definition, never the membership result",
         "population intelligence never mutates source cases"),
        "chained hash(state, previous)", "create/version changes audited",
        "parents reach the member source lineage nodes"),
    "PopulationAnalytics": EntityContract(
        "PopulationAnalytics", INTEL_ANALYTICS_VERSION, ("analytics_id", "scope", "blocks"),
        ("distribution totals equal the sum of their counts", "ratios in [0, 1]",
         "derived only — references + statistics, never source copies"),
        "chained hash(state, previous)", "analytics changes audited",
        "parents reach the source population lineage nodes"),
    "Trend": EntityContract(
        "Trend", INTEL_TREND_VERSION, ("trend_id", "scope", "series"),
        ("series ordered over a deterministic ordinal dimension (no wall-clock)",
         "direction in {increasing,decreasing,flat,insufficient_data}"),
        "chained hash(state, previous)", "trend changes audited",
        "parents reach the source population lineage nodes"),
    "QualityReport": EntityContract(
        "QualityReport", INTEL_QUALITY_VERSION, ("quality_id", "scope", "metrics"),
        ("every metric value in [0, 1]", "numerator <= denominator"),
        "chained hash(state, previous)", "quality changes audited",
        "parents reach the source population lineage nodes"),
    "IntelligenceReport": EntityContract(
        "IntelligenceReport", INTEL_REPORT_VERSION, ("report_id", "report_type", "scope"),
        ("references point at registered intelligence artifacts",),
        "chained hash(state, previous)", "report creation audited",
        "parents reach the referenced artifact lineage nodes"),
    "IntelRegistryRecord": EntityContract(
        "IntelRegistryRecord", INTEL_REGISTRY_VERSION,
        ("artifact_id", "artifact_kind", "version", "lineage_id"),
        ("no intelligence artifact exists outside the registry",
         "silent overwrite with different content forbidden"),
        "tracks the current artifact version", "registry changes audited",
        "lineage_id references the artifact lineage node"),
    "IntelAuditRecord": EntityContract(
        "IntelAuditRecord", INTEL_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)", "prev_hash links the chain"),
        "n/a", "immutable; append-only; tamper-evident", "n/a"),
    "IntelLineageRecord": EntityContract(
        "IntelLineageRecord", INTEL_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "n/a", "lineage changes audited", "parents reach source population nodes"),
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
