"""Entity contracts for the decision-support domain (V2-P6)."""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    DECISION_CONTEXT_VERSION, DECISION_EVIDENCE_VERSION, DECISION_RISK_VERSION,
    DECISION_PRIORITIZATION_VERSION, DECISION_GUIDANCE_VERSION, DECISION_DOMAIN_VERSION,
    DECISION_REGISTRY_VERSION, DECISION_AUDIT_VERSION,
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
    "DecisionContext": EntityContract(
        "DecisionContext", DECISION_CONTEXT_VERSION, ("context_id", "case_id", "patient_id"),
        ("context_id matches /^decision_context\\+[0-9a-f]{16}$/",
         "aggregates references only; never copies/mutates source records"),
        "chained hash(state, previous)", "context creation audited",
        "parents reach case/review/finding/interpretation/concept nodes"),
    "EvidenceBundle": EntityContract(
        "EvidenceBundle", DECISION_EVIDENCE_VERSION, ("bundle_id", "context_id", "items"),
        ("includes ALL evidence in the context (no evidence hidden)",
         "ranks are 1..n contiguous; item order equals ranking",
         "evidence confidence is the recorded V1 value, never recomputed"),
        "chained hash(state, previous)", "bundle creation audited",
        "parents reach the context node"),
    "RiskContext": EntityContract(
        "RiskContext", DECISION_RISK_VERSION, ("risk_id", "context_id", "components"),
        ("seven explainable components, each with a basis", "values + aggregate in [0,1]",
         "aggregate equals the component mean", "review-attention risk, NOT a clinical risk score"),
        "chained hash(state, previous)", "risk changes audited", "parents reach the context node"),
    "PrioritizationRecord": EntityContract(
        "PrioritizationRecord", DECISION_PRIORITIZATION_VERSION,
        ("priority_id", "context_id", "level", "score"),
        ("factor contributions sum exactly to the score (explainable)",
         "score in [0,1]", "orders reviewer attention only; not clinical triage"),
        "chained hash(state, previous)", "prioritization changes audited",
        "parents reach context + risk nodes"),
    "GuidanceRecord": EntityContract(
        "GuidanceRecord", DECISION_GUIDANCE_VERSION, ("guidance_id", "context_id", "items"),
        ("process-only categories (review/evidence/knowledge/investigation/risk)",
         "NO diagnosis/treatment/medication/clinical-order language (scope guard)",
         "every item carries a rationale + references"),
        "chained hash(state, previous)", "guidance changes audited",
        "parents reach context + risk + prioritization nodes"),
    "DecisionSupportRecord": EntityContract(
        "DecisionSupportRecord", DECISION_DOMAIN_VERSION,
        ("record_id", "case_id", "context_id", "guidance_id"),
        ("links context/evidence/risk/prioritization/guidance",
         "explanation states the clinician remains the decision-maker"),
        "chained hash(state, previous)", "record creation audited",
        "parents reach all component nodes"),
    "DecisionRegistryRecord": EntityContract(
        "DecisionRegistryRecord", DECISION_REGISTRY_VERSION,
        ("artifact_id", "artifact_kind", "version", "lineage_id"),
        ("no decision artifact exists outside the registry",
         "silent overwrite with different content forbidden"),
        "tracks the current artifact version", "registry changes audited",
        "lineage_id references the artifact lineage node"),
    "DecisionAuditRecord": EntityContract(
        "DecisionAuditRecord", DECISION_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)", "prev_hash links the chain"),
        "n/a", "immutable; append-only; tamper-evident", "n/a"),
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
