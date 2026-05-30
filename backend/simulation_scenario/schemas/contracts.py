"""Entity contracts for the simulation/scenario domain (V4-P9).

Each mandated entity declares its schema (required fields), validation rules, version
rule, audit rule, and lineage rule — the directive's per-entity contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..version import (
    SIMULATION_DOMAIN_VERSION, SIMULATION_IDENTITY_VERSION, SIMULATION_CONTEXT_VERSION,
    SIMULATION_FORECAST_VERSION, SIMULATION_COMPARISON_VERSION, SIMULATION_RISK_VERSION,
    SIMULATION_AUDIT_VERSION, SIMULATION_LINEAGE_VERSION, SIMULATION_REGISTRY_VERSION,
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
    "ScenarioIdentity": EntityContract(
        "ScenarioIdentity", SIMULATION_IDENTITY_VERSION, ("id", "scenario_type", "name"),
        ("id matches /^scenario\\+[0-9a-f]{16}$/", "id derives from type + name + signature"),
        "stable across re-derivation", "minting audited via build", "n/a"),
    "ScenarioContext": EntityContract(
        "ScenarioContext", SIMULATION_CONTEXT_VERSION,
        ("focus_kind", "observations", "governance_summary"),
        ("content-addressed; reproducible (same inputs -> same signature)",
         "read-only snapshot; production state never touched"),
        "n/a", "n/a", "parents are the observed artifacts' lineage nodes"),
    "ScenarioRecord": EntityContract(
        "ScenarioRecord", SIMULATION_DOMAIN_VERSION,
        ("scenario_id", "scenario_type", "name", "context"),
        ("scenario_type in the closed scenario-type set",
         "a scenario is a hypothesis; it never executes"),
        "chained hash(state, previous)", "creation audited",
        "parents trace to the observed artifacts (reach the patient)"),
    "SimulationRecord": EntityContract(
        "SimulationRecord", SIMULATION_DOMAIN_VERSION,
        ("simulation_id", "scenario_id", "result"),
        ("deterministic (no randomness); same scenario -> same result",
         "evaluation only; never executes/authorizes/mutates"),
        "chained hash(state, previous)", "run + version audited",
        "parents are the scenario + evaluated artifacts' nodes"),
    "SimulationResult": EntityContract(
        "SimulationResult", SIMULATION_DOMAIN_VERSION,
        ("outcomes", "forecasts", "risks", "readiness_score"),
        ("readiness_score in [0,1]; outcome status in {ready,degraded,blocked}",),
        "part of the simulation state signature", "n/a", "n/a"),
    "SimulationOutcome": EntityContract(
        "SimulationOutcome", SIMULATION_DOMAIN_VERSION, ("dimension", "status", "score"),
        ("dimension is a known effect dimension; score in [0,1]",),
        "part of the simulation state signature", "n/a", "n/a"),
    "ForecastRecord": EntityContract(
        "ForecastRecord", SIMULATION_FORECAST_VERSION,
        ("forecast_id", "forecast_type", "projected_status", "confidence"),
        ("forecast_type in the closed set; confidence in [0,1]",
         "explainable (factors + explanation present); never random"),
        "part of the simulation state signature", "generation audited", "n/a"),
    "ComparisonRecord": EntityContract(
        "ComparisonRecord", SIMULATION_COMPARISON_VERSION,
        ("comparison_id", "scenario_ids", "recommended_scenario_id"),
        (">= 2 scenarios compared; recommended is one of them",
         "recommends only; never executes the recommendation"),
        "chained hash(state, previous)", "generation audited",
        "parents are the compared simulations' nodes"),
    "SimulationRiskRecord": EntityContract(
        "SimulationRiskRecord", SIMULATION_RISK_VERSION,
        ("risk_id", "dimension", "score", "level"),
        ("dimension in the closed risk-dimension set; score in [0,1]; explainable",),
        "part of the simulation state signature", "n/a", "n/a"),
    "SimulationVersion": EntityContract(
        "SimulationVersion", SIMULATION_DOMAIN_VERSION, ("version", "previous", "reason"),
        ("version = hash(state_signature, previous)",),
        "content-addressed; chained", "version changes audited", "n/a"),
    "SimulationAuditRecord": EntityContract(
        "SimulationAuditRecord", SIMULATION_AUDIT_VERSION,
        ("seq", "kind", "prev_hash", "event_hash"),
        ("event_hash = hash(seq, kind, payload, prev_hash, created_at)",),
        "n/a", "immutable; append-only; tamper-evident", "n/a"),
    "SimulationLineageRecord": EntityContract(
        "SimulationLineageRecord", SIMULATION_LINEAGE_VERSION, ("lineage_id", "kind"),
        ("lineage_id matches /^lineage\\+[0-9a-f]{16}$/",),
        "n/a", "lineage creation audited",
        "parents are the evaluated artifacts' nodes (reach the patient)"),
    "SimulationRegistryRecord": EntityContract(
        "SimulationRegistryRecord", SIMULATION_REGISTRY_VERSION,
        ("artifact_id", "artifact_kind", "version", "lineage_id"),
        ("no simulation artifact exists outside the registry",
         "silent overwrite with different content forbidden"),
        "tracks the current artifact version", "registry changes audited",
        "lineage_id references the artifact lineage node"),
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
    return {"simulation_domain_version": SIMULATION_DOMAIN_VERSION,
            "contracts": {name: c.to_dict() for name, c in sorted(ENTITY_CONTRACTS.items())}}
