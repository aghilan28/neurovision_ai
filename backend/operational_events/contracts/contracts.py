"""Entity contracts for the operational-event domain (V3-P1).

Each entity declares its Schema · Version · Validation Rules · Version Rules ·
Audit Rules · Lineage Rules in one versioned object (mirrors the convention used
by clinical_cases/findings/knowledge and the V2 intelligence/decision layers).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    EVENT_DOMAIN_VERSION, EVENT_IDENTITY_VERSION, EVENT_TAXONOMY_VERSION,
    EVENT_REGISTRY_VERSION, EVENT_RELATIONSHIP_VERSION, EVENT_AUDIT_VERSION,
    EVENT_LINEAGE_VERSION,
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
    "EventIdentity": EntityContract(
        "EventIdentity", EVENT_IDENTITY_VERSION,
        ("id", "event_type", "category", "source_entity_id", "source_version", "clock"),
        ("id matches /^event\\+[0-9a-f]{16}$/",
         "id derives from source entity + source version + type + logical clock",
         "logical clock is deterministic (ingestion ordinal + source seq + epoch), never wall-clock"),
        "identity is immutable; a new occurrence mints a new id",
        "minting is audited via the owning event's creation", "n/a"),
    "EventRecord": EntityContract(
        "EventRecord", EVENT_DOMAIN_VERSION,
        ("event_id", "event_type", "category", "source_entity_id", "clock", "metadata"),
        ("an event is a fact: immutable, never edited",
         "(category, type) must exist in the taxonomy",
         "metadata pins the source audit event hash it was observed from",
         "supersession references a prior event; it never rewrites it"),
        "chained hash(state, previous); content excludes governance bookkeeping",
        "creation/registration/supersession/version changes audited",
        "parents reach the source entity lineage node (back to the patient)"),
    "EventType/EventCategory": EntityContract(
        "EventType/EventCategory", EVENT_TAXONOMY_VERSION, ("category", "type"),
        ("category in the closed taxonomy", "type permitted for its category",
         "governance/quality/validation actions are first-class categories"),
        "taxonomy is versioned; types are globally unique", "n/a", "n/a"),
    "EventRelationship": EntityContract(
        "EventRelationship", EVENT_RELATIONSHIP_VERSION,
        ("relationship_id", "source_event_id", "target_id", "target_kind", "relation"),
        ("relationship_id matches /^eventrel\\+[0-9a-f]{16}$/",
         "relation in {observes, causal, sequence, depends_on, supersedes}",
         "endpoints reference registered artifacts/events"),
        "relationships are immutable facts", "relationship creation audited",
        "supports causal / dependency / sequence chains"),
    "EventVersion": EntityContract(
        "EventVersion", EVENT_DOMAIN_VERSION, ("version", "reason"),
        ("version = hash(state_signature, previous)",),
        "content-addressed; supersession bumps version", "version changes audited", "n/a"),
    "EventAuditRecord": EntityContract(
        "EventAuditRecord", EVENT_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)", "prev_hash links the chain"),
        "n/a", "immutable; append-only; tamper-evident", "n/a"),
    "EventLineageRecord": EntityContract(
        "EventLineageRecord", EVENT_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "n/a", "lineage creation audited",
        "parents reach the observed source entity node (Patient → ... → Event)"),
    "EventRegistryRecord": EntityContract(
        "EventRegistryRecord", EVENT_REGISTRY_VERSION,
        ("event_id", "event_type", "category", "version", "lineage_id", "status"),
        ("no event exists outside the registry",
         "silent overwrite with different content forbidden",
         "status in {active, superseded}"),
        "tracks the current event version", "registry changes audited",
        "lineage_id references the event lineage node"),
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
