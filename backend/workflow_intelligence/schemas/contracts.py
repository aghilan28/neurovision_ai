"""Entity contracts for the workflow-intelligence domain (V3-P3)."""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    WORKFLOW_DOMAIN_VERSION, WORKFLOW_IDENTITY_VERSION, WORKFLOW_TRANSITION_VERSION,
    WORKFLOW_DEPENDENCY_VERSION, WORKFLOW_METRIC_VERSION, WORKFLOW_REGISTRY_VERSION,
    WORKFLOW_AUDIT_VERSION, WORKFLOW_LINEAGE_VERSION,
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
    "WorkflowIdentity": EntityContract(
        "WorkflowIdentity", WORKFLOW_IDENTITY_VERSION, ("id", "workflow_type", "subject_id"),
        ("id matches /^workflow\\+[0-9a-f]{16}$/",
         "id derives from workflow type + subject (definition, not result)"),
        "identity stable across re-derivation", "minting audited via workflow creation", "n/a"),
    "WorkflowRecord": EntityContract(
        "WorkflowRecord", WORKFLOW_DOMAIN_VERSION,
        ("workflow_id", "workflow_type", "subject_kind", "subject_id", "state"),
        ("a workflow is derived from events + temporal intelligence (no hidden state)",
         "state equals the last transition's to_state (or 'empty')",
         "transitions are contiguous + continuous"),
        "chained hash(state, previous)", "creation/update/metric/version changes audited",
        "parents reach the source event/timeline nodes (back to the patient)"),
    "WorkflowTransition": EntityContract(
        "WorkflowTransition", WORKFLOW_TRANSITION_VERSION,
        ("order", "to_state", "event_id", "event_type"),
        ("from_state equals the previous transition's to_state",
         "derived from a lifecycle event"),
        "immutable within a workflow version", "transition analysis audited", "references its source event"),
    "WorkflowDependency": EntityContract(
        "WorkflowDependency", WORKFLOW_DEPENDENCY_VERSION,
        ("dependency_id", "from_entity", "to_entity", "relation"),
        ("relation in {upstream, downstream, blocked, waiting, completed}",
         "endpoints reference real operational entities"),
        "immutable within a workflow version", "dependency changes audited",
        "supports upstream/downstream/blocked/waiting/completed"),
    "WorkflowMetric": EntityContract(
        "WorkflowMetric", WORKFLOW_METRIC_VERSION, ("name", "value", "unit", "observed"),
        ("ratio metrics in [0,1]", "deterministic; no wall-clock (durations in logical steps)"),
        "immutable within a workflow version", "metric generation audited", "n/a"),
    "WorkflowRegistryRecord": EntityContract(
        "WorkflowRegistryRecord", WORKFLOW_REGISTRY_VERSION,
        ("workflow_id", "workflow_type", "version", "lineage_id"),
        ("no workflow exists outside the registry",
         "silent overwrite with different content forbidden"),
        "tracks the current workflow version", "registry changes audited",
        "lineage_id references the workflow lineage node"),
    "WorkflowAuditRecord": EntityContract(
        "WorkflowAuditRecord", WORKFLOW_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)", "prev_hash links the chain"),
        "n/a", "immutable; append-only; tamper-evident", "n/a"),
    "WorkflowLineageRecord": EntityContract(
        "WorkflowLineageRecord", WORKFLOW_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "n/a", "lineage creation audited", "parents reach the source event/timeline nodes"),
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
