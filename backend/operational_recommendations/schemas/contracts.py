"""Entity contracts for the operational-recommendation domain (V3-P6)."""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    RECOMMENDATION_DOMAIN_VERSION, RECOMMENDATION_IDENTITY_VERSION,
    RECOMMENDATION_CONTEXT_VERSION, RECOMMENDATION_EVIDENCE_VERSION,
    RECOMMENDATION_PRIORITY_VERSION, RECOMMENDATION_REGISTRY_VERSION,
    RECOMMENDATION_AUDIT_VERSION, RECOMMENDATION_LINEAGE_VERSION,
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
    "RecommendationIdentity": EntityContract(
        "RecommendationIdentity", RECOMMENDATION_IDENTITY_VERSION, ("id", "kind", "scope"),
        ("id matches /^recommendation\\+[0-9a-f]{16}$/",
         "id derives from kind + scope (definition, not result)"),
        "identity stable across re-derivation", "minting audited via recommendation creation",
        "n/a"),
    "RecommendationRecord": EntityContract(
        "RecommendationRecord", RECOMMENDATION_DOMAIN_VERSION,
        ("recommendation_id", "kind", "scope", "subject_kind", "subject_id", "statement"),
        ("operational only (never clinical decision support/diagnosis/treatment)",
         "evidence-linked AND analytics-linked (no black-box recommendation)",
         "explainable: statement + rationale + priority reason present",
         "a suggestion only — never executed, never auto-escalated"),
        "chained hash(state, previous)", "creation/generation/version changes audited",
        "parents reach the analytics/workflow/graph nodes (back to the patient)"),
    "RecommendationContext": EntityContract(
        "RecommendationContext", RECOMMENDATION_CONTEXT_VERSION, ("context_id", "scope"),
        ("aggregates analytics/workflow/graph/temporal/risk/health context",
         "a derived view — adds no new truth"),
        "content-addressed; immutable per content", "context build audited",
        "derived from analytics records"),
    "RecommendationEvidence": EntityContract(
        "RecommendationEvidence", RECOMMENDATION_EVIDENCE_VERSION,
        ("evidence_id", "source_kind", "source_id"),
        ("every evidence item references a real upstream artifact",
         "source_kind in {analytics, workflow, graph_node, event, temporal_analytics}"),
        "immutable within a recommendation version", "evidence citation audited",
        "lineage_id (when present) parents the recommendation lineage node"),
    "RecommendationPriority": EntityContract(
        "RecommendationPriority", RECOMMENDATION_PRIORITY_VERSION, ("level", "score", "reason"),
        ("level in {low, medium, high, critical}", "score in [0,1] banded deterministically",
         "explainable: reason + supporting signals present"),
        "immutable within a recommendation version", "prioritization audited", "n/a"),
    "RecommendationRegistryRecord": EntityContract(
        "RecommendationRegistryRecord", RECOMMENDATION_REGISTRY_VERSION,
        ("recommendation_id", "kind", "version", "lineage_id"),
        ("no recommendation exists outside the registry",
         "silent overwrite with different content forbidden"),
        "tracks the current recommendation version", "registry changes audited",
        "lineage_id references the recommendation lineage node"),
    "RecommendationAuditRecord": EntityContract(
        "RecommendationAuditRecord", RECOMMENDATION_AUDIT_VERSION,
        ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",
         "prev_hash links the chain"),
        "n/a", "immutable; append-only; tamper-evident", "n/a"),
    "RecommendationLineageRecord": EntityContract(
        "RecommendationLineageRecord", RECOMMENDATION_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "n/a", "lineage creation audited",
        "parents reach the analytics/workflow/graph nodes"),
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
    return {"recommendation_domain_version": RECOMMENDATION_DOMAIN_VERSION,
            "contracts": {name: c.to_dict() for name, c in sorted(ENTITY_CONTRACTS.items())}}
