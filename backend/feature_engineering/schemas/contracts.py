"""Entity contracts for the Feature Engineering domain (no undocumented objects).

For each entity: Schema (required fields) · Validation Rules · Lineage Rule · Audit
Rule. ``validate_entity`` checks an entity's serialized form against its schema.
Mirrors ``backend.signal_processing.schemas.contracts``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    FEATURE_DOMAIN_VERSION, FEATURE_IDENTITY_VERSION, FEATURE_REGISTRY_VERSION,
    FEATURE_AUDIT_VERSION, FEATURE_LINEAGE_VERSION, FEATURE_VALIDATION_VERSION,
    FEATURE_REPORT_VERSION,
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
    "FeatureIdentity": EntityContract(
        "FeatureIdentity", FEATURE_IDENTITY_VERSION,
        ("feature_asset_id", "processed_id", "identity_version"),
        ("feature_asset_id matches /^feature\\+[0-9a-f]{16}$/",
         "content-addressed from processed id + extraction fingerprint (never filename)"),
        "derived_from = processed_id", "minted-once; never modified"),
    "FeatureRecord": EntityContract(
        "FeatureRecord", FEATURE_DOMAIN_VERSION,
        ("identity", "processed_id", "eeg_asset_id", "case_id", "patient_id", "groups",
         "metadata", "validation", "status", "version"),
        ("immutable (frozen) once generated", "carries no raw signal",
         "derived from an immutable processed EEG asset"),
        "lineage node parents the processed-EEG node (Patient -> Case -> EEG -> Processed -> Feature)",
        "every extraction/validation/lineage/version/registration event audited"),
    "FeatureVector": EntityContract(
        "FeatureVector", FEATURE_DOMAIN_VERSION,
        ("name", "family", "group", "scope", "values", "shape"),
        ("family is a closed FeatureFamily", "group is a closed FeatureGroup",
         "scope is a closed FeatureScope", "prod(shape) == n_values", "content-addressed"),
        "n/a (atomic output)", "n/a"),
    "FeatureGroupRecord": EntityContract(
        "FeatureGroupRecord", FEATURE_DOMAIN_VERSION, ("family", "vectors"),
        ("family is a closed FeatureFamily", "groups vectors of one family"), "n/a", "n/a"),
    "FeatureMetadata": EntityContract(
        "FeatureMetadata", FEATURE_DOMAIN_VERSION,
        ("processed_id", "eeg_asset_id", "n_channels", "sampling_frequency", "families_present"),
        ("deterministic (pure function of the processed signal + config)",
         "records families/groups present + extraction config"),
        "n/a", "n/a"),
    "FeatureValidationRecord": EntityContract(
        "FeatureValidationRecord", FEATURE_VALIDATION_VERSION, ("validation_id", "ok", "checks"),
        ("content checks: completeness/integrity/consistency/determinism",
         "structured (name, passed, detail); never exceptions"),
        "n/a", "validation recorded in the audit trail"),
    "FeatureRegistryRecord": EntityContract(
        "FeatureRegistryRecord", FEATURE_REGISTRY_VERSION,
        ("feature_asset_id", "processed_id", "eeg_asset_id", "case_id", "patient_id",
         "status", "version", "lineage_id"),
        ("no feature asset exists outside the registry",
         "silent overwrite with different content forbidden"),
        "lineage_id references the feature lineage node", "registry changes audited"),
    "FeatureAuditRecord": EntityContract(
        "FeatureAuditRecord", FEATURE_AUDIT_VERSION, ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",
         "prev_hash links to the previous event (chain)"),
        "n/a", "immutable; append-only; tamper-evident (shared ImmutableAuditLog)"),
    "FeatureLineageRecord": EntityContract(
        "FeatureLineageRecord", FEATURE_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "parents reference the processed-EEG lineage node", "lineage event audited"),
    "FeatureReport": EntityContract(
        "FeatureReport", FEATURE_REPORT_VERSION, ("report_type", "feature_report_version"),
        ("deterministic; reproducible for a given asset/registry state",), "n/a", "n/a"),
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
