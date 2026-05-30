"""Entity contracts for the Application Backend domain (no undocumented objects, P6-M).

For each entity: Schema (required fields) · Validation Rules · Lineage Rule · Audit
Rule. ``validate_entity`` checks an entity's serialized form against its schema.
Mirrors ``backend.inference_foundation.schemas.contracts``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    APPLICATION_DOMAIN_VERSION, APPLICATION_IDENTITY_VERSION, APPLICATION_AUTH_VERSION,
    APPLICATION_USERS_VERSION, APPLICATION_WORKFLOW_VERSION, APPLICATION_API_VERSION,
    APPLICATION_REGISTRY_VERSION, APPLICATION_AUDIT_VERSION, APPLICATION_LINEAGE_VERSION,
    APPLICATION_VALIDATION_VERSION, APPLICATION_REPORT_VERSION,
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
    "UserIdentity": EntityContract(
        "UserIdentity", APPLICATION_IDENTITY_VERSION, ("user_id", "username"),
        ("user_id matches /^user\\+[0-9a-f]{16}$/", "content-addressed from username"),
        "user node is a lineage root", "minted-once; never modified"),
    "UserRecord": EntityContract(
        "UserRecord", APPLICATION_USERS_VERSION,
        ("identity", "roles", "status", "version"),
        ("roles are a closed UserRole set", "status is a closed UserStatus",
         "carries NO secret material (no password/salt)"),
        "lineage_id references the user node", "create/update/status/version events audited"),
    "SessionRecord": EntityContract(
        "SessionRecord", APPLICATION_AUTH_VERSION,
        ("session_id", "user_id", "token_fingerprint", "status", "version"),
        ("stores only a token fingerprint, never the raw token",
         "status is a closed SessionStatus", "session_id content-addressed from user + token fp"),
        "session node parents the user node", "create/revoke/version events audited"),
    "UploadRecord": EntityContract(
        "UploadRecord", APPLICATION_DOMAIN_VERSION,
        ("upload_id", "user_id", "filename", "content_fingerprint", "status"),
        ("content_fingerprint = sha256 of the uploaded bytes", "status is a closed UploadStatus"),
        "upload node parents the user node (User -> Upload)", "upload receipt audited"),
    "RequestRecord": EntityContract(
        "RequestRecord", APPLICATION_DOMAIN_VERSION,
        ("request_id", "operation", "api_version", "status"),
        ("operation is a closed ApiOperation", "params_fingerprint is content-derived"),
        "n/a", "every request recorded in the audit trail"),
    "ResponseRecord": EntityContract(
        "ResponseRecord", APPLICATION_DOMAIN_VERSION,
        ("response_id", "request_id", "status", "body_fingerprint"),
        ("status is a closed ResponseStatus", "references its request"),
        "n/a", "every response recorded in the audit trail"),
    "WorkflowRecord": EntityContract(
        "WorkflowRecord", APPLICATION_WORKFLOW_VERSION,
        ("workflow_id", "upload_id", "user_id", "eeg_asset_id", "processed_id",
         "feature_asset_id", "model_id", "prediction_id", "stages", "status", "version"),
        ("stages are a closed ordered WorkflowStage set", "status is a closed WorkflowStatus",
         "references reused P1-P5 artifacts; duplicates no business logic"),
        "workflow join node parents the upload node + the prediction node "
        "(User -> Upload -> ... -> Prediction)",
        "every stage + version + completion event audited"),
    "AnalysisRecord": EntityContract(
        "AnalysisRecord", APPLICATION_DOMAIN_VERSION,
        ("analysis_id", "workflow_id", "prediction_id", "status"),
        ("summary references the P5 prediction asset (no duplicated result)",
         "status is a closed AnalysisStatus"),
        "lineage_id references the workflow join node", "analysis generation audited"),
    "APIRecord": EntityContract(
        "APIRecord", APPLICATION_API_VERSION, ("api_id", "name", "api_version", "operations"),
        ("operations are the closed ApiOperation set", "versioned (v1)"),
        "n/a", "n/a"),
    "BackendRegistryRecord": EntityContract(
        "BackendRegistryRecord", APPLICATION_REGISTRY_VERSION,
        ("entity_kind", "entity_id", "status", "version", "lineage_id", "audit_state"),
        ("no orphan records (every entry has an audit head + lineage node)",
         "silent overwrite with different content forbidden"),
        "lineage_id references the entity's lineage node", "registry changes governed"),
    "BackendAuditRecord": EntityContract(
        "BackendAuditRecord", APPLICATION_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",
         "prev_hash links to the previous event (chain)"),
        "n/a", "immutable; append-only; tamper-evident (shared ImmutableAuditLog)"),
    "BackendLineageRecord": EntityContract(
        "BackendLineageRecord", APPLICATION_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "recorded in the single shared LineageTracker (no parallel system)", "lineage event audited"),
    "BackendValidationRecord": EntityContract(
        "BackendValidationRecord", APPLICATION_VALIDATION_VERSION, ("validation_id", "ok", "checks"),
        ("structured (name, passed, detail); never exceptions",), "n/a",
        "validation recorded in the audit trail"),
    "ApplicationReport": EntityContract(
        "ApplicationReport", APPLICATION_REPORT_VERSION, ("report_type", "application_report_version"),
        ("deterministic; reproducible for a given state",), "n/a", "n/a"),
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
