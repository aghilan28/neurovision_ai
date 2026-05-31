"""``backend/application_platform/schemas`` — entity contracts (Track 3).

A documented contract per entity (no undocumented objects). ``validate_entity`` checks a
serialized entity against its contract's required fields.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    APP_PREDICTION_VERSION, APP_READINESS_VERSION, APP_REGISTRY_VERSION,
    APP_REPORT_VERSION, APP_UPLOAD_VERSION, APP_WORKFLOW_VERSION,
)


@dataclass(frozen=True)
class EntityContract:
    name: str
    version: str
    required_fields: tuple
    rules: tuple

    def to_dict(self) -> dict:
        return {"name": self.name, "version": self.version,
                "required_fields": list(self.required_fields), "rules": list(self.rules)}


ENTITY_CONTRACTS: dict = {
    "UploadRecord": EntityContract(
        "UploadRecord", APP_UPLOAD_VERSION,
        ("upload_id", "user_id", "filename", "content_fingerprint", "status"),
        ("format in EDF/EDF+/BDF/BDF+", "validated from the actual bytes",
         "analysis bounded to a leading segment; full upload preserved")),
    "PredictionRequestRecord": EntityContract(
        "PredictionRequestRecord", APP_PREDICTION_VERSION,
        ("prediction_request_id", "upload_id", "user_id", "model_id"),
        ("references a real upload + a Track-2 model",)),
    "PredictionResultRecord": EntityContract(
        "PredictionResultRecord", APP_PREDICTION_VERSION,
        ("prediction_result_id", "prediction_request_id", "predicted_label", "model_id"),
        ("carries prediction + confidence + calibration + model + evidence",
         "all derived from the reused inference; never recomputed here")),
    "WorkflowRecord": EntityContract(
        "WorkflowRecord", APP_WORKFLOW_VERSION,
        ("workflow_id", "upload_id", "analysis_id", "stages", "status"),
        ("stages: upload->validate->metadata->features->select_model->inference->results->report",)),
    "ReportRecord": EntityContract(
        "ReportRecord", APP_REPORT_VERSION,
        ("report_id", "analysis_id", "report_type", "available_formats"),
        ("exports JSON / HTML / PDF deterministically",)),
    "ReadinessRecord": EntityContract(
        "ReadinessRecord", APP_READINESS_VERSION,
        ("readiness_id", "subject", "score", "classification", "dimensions"),
        ("classification in NOT_READY/PARTIALLY_READY/READY_FOR_USERS",
         "READY_FOR_USERS requires a complete, traceable user workflow")),
    "ApplicationRegistryRecord": EntityContract(
        "ApplicationRegistryRecord", APP_REGISTRY_VERSION,
        ("entity_kind", "entity_id", "version", "lineage_id", "audit_state"),
        ("no orphan records (audit head + lineage node required)",)),
}


def contract_for(name: str) -> EntityContract:
    if name not in ENTITY_CONTRACTS:
        raise KeyError(f"no contract for entity {name!r}")
    return ENTITY_CONTRACTS[name]


def validate_entity(name: str, entity_dict: dict) -> tuple:
    contract = contract_for(name)
    missing = [f for f in contract.required_fields
               if f not in entity_dict or entity_dict[f] in (None, "")]
    return (len(missing) == 0), missing


__all__ = ["EntityContract", "ENTITY_CONTRACTS", "contract_for", "validate_entity"]
