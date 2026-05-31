"""Entity contracts for the Serving domain (DRP3-L; no undocumented objects).

For each entity: Schema (required fields) · Validation Rules · Lineage Rule · Audit Rule.
``validate_entity`` checks an entity's serialized form against its schema. Mirrors
``backend.inference_foundation.schemas.contracts``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    SERVING_DOMAIN_VERSION, SERVING_IDENTITY_VERSION, SERVING_LIFECYCLE_VERSION,
    SERVING_READINESS_VERSION, SERVING_REGISTRY_VERSION, SERVING_AUDIT_VERSION,
    SERVING_LINEAGE_VERSION, SERVING_VALIDATION_VERSION, SERVING_CONTRACT_VERSION,
    SERVING_REPORT_VERSION,
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
    "ServingIdentity": EntityContract(
        "ServingIdentity", SERVING_IDENTITY_VERSION,
        ("execution_id", "request_id", "response_id", "model_id", "prediction_id"),
        ("execution_id matches /^serving_execution\\+[0-9a-f]{16}$/",
         "content-addressed from the request + prediction"),
        "derived_from = request_id", "minted-once; never modified"),
    "ServingRequestRecord": EntityContract(
        "ServingRequestRecord", SERVING_DOMAIN_VERSION,
        ("request_id", "model_ref", "feature_asset_id", "case_id", "patient_id"),
        ("model_ref carries a model_id or an architecture",
         "references a registered input feature asset"),
        "request node parents the model node + the input feature node", "request audited"),
    "ServingResponseRecord": EntityContract(
        "ServingResponseRecord", SERVING_DOMAIN_VERSION,
        ("response_id", "request_id", "model_id", "prediction_id", "predicted_class",
         "probability_scores", "confidence_level", "calibration_quality"),
        ("reuses the inference asset; duplicates no prediction logic",
         "confidence + calibration always delivered alongside the label (NR-4)"),
        "response node parents the execution node", "response audited"),
    "ServingExecutionRecord": EntityContract(
        "ServingExecutionRecord", SERVING_DOMAIN_VERSION,
        ("identity", "request", "response", "lifecycle", "model_id", "prediction_id",
         "validation", "readiness_id", "status", "version"),
        ("immutable (frozen) once served", "binds request + model + inference + response",
         "carries derived ids/signatures, never model weights"),
        "execution node parents the request node + the inference prediction node",
        "every lifecycle/validation/readiness/version/registration event audited"),
    "ServingLifecycleRecord": EntityContract(
        "ServingLifecycleRecord", SERVING_LIFECYCLE_VERSION, ("request_id", "transitions", "final_state"),
        ("transitions follow the canonical order",
         "request_created -> ... -> execution_completed"),
        "n/a", "lifecycle transitions audited"),
    "ServingValidationRecord": EntityContract(
        "ServingValidationRecord", SERVING_VALIDATION_VERSION, ("validation_id", "ok", "checks"),
        ("checks: request/model/feature/execution/response/contract/version",
         "structured (name, passed, detail); never exceptions"),
        "n/a", "validation recorded in the audit trail"),
    "ServingReadinessRecord": EntityContract(
        "ServingReadinessRecord", SERVING_READINESS_VERSION,
        ("readiness_id", "target_id", "score", "classification", "dimensions"),
        ("six dimensions (execution/contract/validation/registry/audit/lineage)",
         "READY requires all present + validation passes"),
        "readiness references the served execution", "readiness audited"),
    "ServingRegistryRecord": EntityContract(
        "ServingRegistryRecord", SERVING_REGISTRY_VERSION,
        ("execution_id", "request_id", "response_id", "model_id", "prediction_id", "status",
         "version", "lineage_id"),
        ("no execution exists outside the registry; no orphans",
         "cross-references the shared model + prediction ids; silent overwrite forbidden"),
        "lineage_id references the serving-execution node", "registry changes audited"),
    "ServingAuditRecord": EntityContract(
        "ServingAuditRecord", SERVING_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",
         "prev_hash links to the previous event (chain)"),
        "n/a", "immutable; append-only; tamper-evident (shared ImmutableAuditLog)"),
    "ServingLineageRecord": EntityContract(
        "ServingLineageRecord", SERVING_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "parents reference the upstream lineage node", "lineage event audited"),
    "ServingContract": EntityContract(
        "ServingContract", SERVING_CONTRACT_VERSION, ("contract", "contract_version"),
        ("versioned request/response/error/finding/metadata contracts",
         "in-process; transport-agnostic (no HTTP)"), "n/a", "n/a"),
    "ServingReport": EntityContract(
        "ServingReport", SERVING_REPORT_VERSION, ("report_type", "serving_report_version"),
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
