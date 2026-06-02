"""``backend/operations_platform/schemas`` — entity contracts (Track 4).

A documented contract per entity (no undocumented objects). ``validate_entity`` checks a
serialized entity against its contract's required fields.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    OPS_DIAGNOSTICS_VERSION, OPS_HEALTH_VERSION, OPS_MONITORING_VERSION, OPS_QUALIFICATION_VERSION,
    OPS_READINESS_VERSION, OPS_REGISTRY_VERSION,
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
    "HealthCheckRecord": EntityContract(
        "HealthCheckRecord", OPS_HEALTH_VERSION,
        ("health_check_id", "overall", "components"),
        ("overall + component states in HEALTHY/DEGRADED/UNHEALTHY",
         "read-only probe of the real product; never modifies a workflow")),
    "MetricsSnapshotRecord": EntityContract(
        "MetricsSnapshotRecord", OPS_MONITORING_VERSION,
        ("metrics_snapshot_id", "deterministic_metrics", "informational_metrics"),
        ("deterministic counts hashed; latency/processing/resource informational (never hashed)",)),
    "DiagnosticRecord": EntityContract(
        "DiagnosticRecord", OPS_DIAGNOSTICS_VERSION,
        ("diagnostic_id", "ok", "findings", "root_causes"),
        ("structured findings with a closed root-cause vocabulary; never exceptions",)),
    "QualificationRecord": EntityContract(
        "QualificationRecord", OPS_QUALIFICATION_VERSION,
        ("qualification_id", "status", "findings"),
        ("status in QUALIFIED/CONDITIONALLY_QUALIFIED/NOT_QUALIFIED",
         "validates dataset/model/api/workflow/report/persistence/security availability")),
    "DeploymentReadinessRecord": EntityContract(
        "DeploymentReadinessRecord", OPS_READINESS_VERSION,
        ("readiness_id", "score", "classification", "dimensions"),
        ("classification in NOT_READY/PARTIALLY_READY/READY_FOR_DEPLOYMENT",
         "READY_FOR_DEPLOYMENT requires healthy + qualified + diagnosed + traceable")),
    "OperationsRegistryRecord": EntityContract(
        "OperationsRegistryRecord", OPS_REGISTRY_VERSION,
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
