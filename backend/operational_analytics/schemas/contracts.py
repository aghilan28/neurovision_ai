"""Entity contracts for the operational-analytics domain (V3-P5)."""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    ANALYTICS_DOMAIN_VERSION, ANALYTICS_IDENTITY_VERSION, ANALYTICS_METRIC_VERSION,
    ANALYTICS_CATEGORY_VERSION, ANALYTICS_REGISTRY_VERSION, ANALYTICS_AUDIT_VERSION,
    ANALYTICS_LINEAGE_VERSION,
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
    "AnalyticsIdentity": EntityContract(
        "AnalyticsIdentity", ANALYTICS_IDENTITY_VERSION, ("id", "category", "scope"),
        ("id matches /^analytics\\+[0-9a-f]{16}$/",
         "id derives from category + scope (definition, not result)"),
        "identity stable across re-derivation", "minting audited via analytics creation", "n/a"),
    "AnalyticsRecord": EntityContract(
        "AnalyticsRecord", ANALYTICS_DOMAIN_VERSION,
        ("analytics_id", "category", "scope", "subject_kind", "subject_id"),
        ("analytics is derived from upstream artifacts (never a source of truth)",
         "category is in the closed analytics-category vocabulary",
         "every metric is explainable + deterministic"),
        "chained hash(state, previous)", "creation/generation/version changes audited",
        "parents reach the source event/workflow/graph/temporal nodes (back to the patient)"),
    "AnalyticsMetric": EntityContract(
        "AnalyticsMetric", ANALYTICS_METRIC_VERSION, ("name", "value", "unit", "observed"),
        ("ratio/score metrics in [0,1]; trend index in [-1,1]",
         "unobserved metrics carry a sentinel value (0.0 or -1.0)",
         "every metric carries a human-readable explanation"),
        "immutable within an analytics version", "metric generation audited", "n/a"),
    "AnalyticsCategory": EntityContract(
        "AnalyticsCategory", ANALYTICS_CATEGORY_VERSION, ("category",),
        ("category in {metrics, health, performance, quality, trend, risk, operational}",),
        "closed vocabulary; extension is a versioned change", "n/a", "n/a"),
    "AnalyticsRegistryRecord": EntityContract(
        "AnalyticsRegistryRecord", ANALYTICS_REGISTRY_VERSION,
        ("analytics_id", "category", "version", "lineage_id"),
        ("no analytics exists outside the registry",
         "silent overwrite with different content forbidden"),
        "tracks the current analytics version", "registry changes audited",
        "lineage_id references the analytics lineage node"),
    "AnalyticsAuditRecord": EntityContract(
        "AnalyticsAuditRecord", ANALYTICS_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)", "prev_hash links the chain"),
        "n/a", "immutable; append-only; tamper-evident", "n/a"),
    "AnalyticsLineageRecord": EntityContract(
        "AnalyticsLineageRecord", ANALYTICS_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "n/a", "lineage creation audited",
        "parents reach the source event/workflow/graph/temporal nodes"),
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
    return {"analytics_domain_version": ANALYTICS_DOMAIN_VERSION,
            "contracts": {name: c.to_dict() for name, c in sorted(ENTITY_CONTRACTS.items())}}
