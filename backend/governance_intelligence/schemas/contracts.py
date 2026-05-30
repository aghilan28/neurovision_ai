"""Entity contracts for the governance-intelligence domain (V4-P7).

Each mandated entity declares its schema (required fields), validation rules,
version rule, audit rule, and lineage rule — the directive's per-entity contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    GOVERNANCE_DOMAIN_VERSION, GOVERNANCE_IDENTITY_VERSION, GOVERNANCE_APPROVAL_VERSION,
    GOVERNANCE_VIOLATION_VERSION, GOVERNANCE_ESCALATION_VERSION, GOVERNANCE_RISK_VERSION,
    GOVERNANCE_METRIC_VERSION, GOVERNANCE_AUDIT_VERSION, GOVERNANCE_LINEAGE_VERSION,
    GOVERNANCE_REGISTRY_VERSION,
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
    "GovernanceIntelligenceIdentity": EntityContract(
        "GovernanceIntelligenceIdentity", GOVERNANCE_IDENTITY_VERSION, ("id", "scope"),
        ("id matches /^govintel\\+[0-9a-f]{16}$/",
         "id derives from scope + content signature"),
        "stable across re-derivation", "minting audited via build", "n/a"),
    "GovernanceIntelligenceRecord": EntityContract(
        "GovernanceIntelligenceRecord", GOVERNANCE_DOMAIN_VERSION,
        ("intelligence_id", "scope", "health_score"),
        ("governance intelligence observes governance; it never modifies it",
         "observed kinds in the closed governed-kind set",
         "health_score in [0,1]; risk scores in [0,1] and explainable"),
        "chained hash(state, previous)", "generation/version audited",
        "parents are the observed artifacts' lineage nodes (reach the patient)"),
    "ApprovalRecord": EntityContract(
        "ApprovalRecord", GOVERNANCE_APPROVAL_VERSION,
        ("approval_id", "entity_kind", "entity_id", "approval_state"),
        ("latency is logical (governance events), never wall-clock",
         "reports an external approval decision; never makes one"),
        "part of the intelligence state signature", "indexed in the registry", "n/a"),
    "ViolationRecord": EntityContract(
        "ViolationRecord", GOVERNANCE_VIOLATION_VERSION,
        ("violation_id", "entity_kind", "entity_id", "violation_type", "severity"),
        ("violation_type in the closed set; severity in {info,low,moderate,high,critical}",
         "detection observes; it never enforces or blocks"),
        "part of the intelligence state signature", "detection audited", "n/a"),
    "EscalationRecord": EntityContract(
        "EscalationRecord", GOVERNANCE_ESCALATION_VERSION,
        ("escalation_id", "entity_kind", "entity_id", "outcome"),
        ("delay is logical (governance events), never wall-clock",
         "analysis observes; it never routes or resolves escalations"),
        "part of the intelligence state signature", "analysis audited", "n/a"),
    "GovernanceRiskRecord": EntityContract(
        "GovernanceRiskRecord", GOVERNANCE_RISK_VERSION,
        ("risk_id", "dimension", "entity_kind", "entity_id", "score", "level"),
        ("dimension in the closed risk-dimension set; score in [0,1]",
         "score is explainable (factors + explanation present)"),
        "part of the intelligence state signature", "risk analysis audited", "n/a"),
    "GovernanceMetric": EntityContract(
        "GovernanceMetric", GOVERNANCE_METRIC_VERSION, ("name", "value"),
        ("metrics are deterministic projections (no wall-clock)",),
        "part of the intelligence state signature", "n/a", "n/a"),
    "GovernanceVersion": EntityContract(
        "GovernanceVersion", GOVERNANCE_DOMAIN_VERSION, ("version", "previous", "reason"),
        ("version = hash(state_signature, previous)",),
        "content-addressed; chained to previous", "version changes audited", "n/a"),
    "GovernanceAuditRecord": EntityContract(
        "GovernanceAuditRecord", GOVERNANCE_AUDIT_VERSION,
        ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",
         "prev_hash links the chain"),
        "n/a", "immutable; append-only; tamper-evident", "n/a"),
    "GovernanceLineageRecord": EntityContract(
        "GovernanceLineageRecord", GOVERNANCE_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "n/a", "lineage creation audited",
        "parents are the observed artifacts' nodes (reach the patient)"),
    "GovernanceRegistryRecord": EntityContract(
        "GovernanceRegistryRecord", GOVERNANCE_REGISTRY_VERSION,
        ("intelligence_id", "scope", "version", "lineage_id"),
        ("no governance-intelligence record exists outside the registry",
         "silent overwrite with different content forbidden"),
        "tracks the current intelligence version", "registry changes audited",
        "lineage_id references the intelligence lineage node"),
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


def all_contracts() -> dict:
    return {"governance_domain_version": GOVERNANCE_DOMAIN_VERSION,
            "contracts": {name: c.to_dict() for name, c in sorted(ENTITY_CONTRACTS.items())}}
