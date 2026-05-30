"""Simulation/scenario domain entities (V4-P9).

Pure data + ``to_dict`` + (where relevant) ``state_signature``. The simulation layer
is a governed **evaluation** environment: it observes and evaluates possible futures;
it never executes, authorizes, or modifies production state. Every entity here is
*derived deterministically* from the already-governed Version 4 artifacts and is
reproducible and auditable.

Mandated entities: ``ScenarioIdentity`` (in ``identity``), ``ScenarioRecord``,
``ScenarioContext``, ``SimulationRecord``, ``SimulationResult``, ``SimulationOutcome``,
``ForecastRecord``, ``ComparisonRecord``, ``SimulationRiskRecord``,
``SimulationVersion``, ``SimulationAuditRecord``, ``SimulationLineageRecord``,
``SimulationRegistryRecord``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    SIMULATION_DOMAIN_VERSION, SIMULATION_CONTEXT_VERSION, SIMULATION_FORECAST_VERSION,
    SIMULATION_COMPARISON_VERSION, SIMULATION_RISK_VERSION, SIMULATION_REGISTRY_VERSION,
    DETERMINISTIC_EPOCH,
)


# --- closed vocabularies ------------------------------------------------------
class ScenarioType:
    GOAL = "goal"
    PLAN = "plan"
    TASK = "task"
    AGENT = "agent"
    EXECUTION = "execution"
    GOVERNANCE = "governance"
    RISK = "risk"


SCENARIO_TYPES: frozenset[str] = frozenset(
    v for k, v in vars(ScenarioType).items() if not k.startswith("_"))


class SimDimension:
    """The deterministic effect dimensions the simulation engine evaluates."""

    POLICY_EFFECTS = "policy_effects"
    CONSTRAINT_EFFECTS = "constraint_effects"
    TASK_DEPENDENCIES = "task_dependencies"
    AGENT_AVAILABILITY = "agent_availability"
    EXECUTION_STRUCTURES = "execution_structures"
    GOVERNANCE_CONTROLS = "governance_controls"


SIM_DIMENSIONS: tuple[str, ...] = (
    SimDimension.POLICY_EFFECTS, SimDimension.CONSTRAINT_EFFECTS,
    SimDimension.TASK_DEPENDENCIES, SimDimension.AGENT_AVAILABILITY,
    SimDimension.EXECUTION_STRUCTURES, SimDimension.GOVERNANCE_CONTROLS,
)


class ForecastType:
    EXECUTION = "execution_forecast"
    RISK = "risk_forecast"
    GOVERNANCE = "governance_forecast"
    APPROVAL = "approval_forecast"
    CONSTRAINT = "constraint_forecast"


FORECAST_TYPES: tuple[str, ...] = (
    ForecastType.EXECUTION, ForecastType.RISK, ForecastType.GOVERNANCE,
    ForecastType.APPROVAL, ForecastType.CONSTRAINT,
)


class SimRiskDimension:
    EXECUTION = "execution_risk"
    GOVERNANCE = "governance_risk"
    POLICY = "policy_risk"
    AGENT = "agent_risk"
    DEPENDENCY = "dependency_risk"
    SCENARIO = "scenario_risk"


SIM_RISK_DIMENSIONS: frozenset[str] = frozenset(
    v for k, v in vars(SimRiskDimension).items() if not k.startswith("_"))


class OutcomeStatus:
    READY = "ready"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


# --- scenario context (frozen, content-addressed, reproducible) --------------
@dataclass(frozen=True)
class ScenarioContext:
    """An immutable, content-addressed snapshot of the observed artifacts a scenario
    evaluates, plus declarative what-if assumptions applied **only** inside the
    simulation (never to production). Reproducible: the same inputs always hash to the
    same context signature.
    """

    focus_kind: str
    observations: tuple                  # tuple[dict]  (GovernedObservation.to_dict())
    assumptions: tuple                   # tuple[tuple[str, str]] sorted (k, json-ish v)
    governance_summary: dict
    parents: tuple[str, ...] = ()
    context_version: str = SIMULATION_CONTEXT_VERSION

    def signature(self) -> str:
        return hash_obj({"focus_kind": self.focus_kind, "observations": list(self.observations),
                         "assumptions": [list(a) for a in self.assumptions],
                         "governance_summary": self.governance_summary})

    def assumptions_dict(self) -> dict:
        return {k: v for k, v in self.assumptions}

    def assumptions_dict_parsed(self) -> dict:
        """Assumptions with their JSON-encoded values decoded back to Python objects."""
        import json
        return {k: json.loads(v) for k, v in self.assumptions}

    def to_dict(self) -> dict:
        return {"focus_kind": self.focus_kind, "n_observations": len(self.observations),
                "observations": list(self.observations),
                "assumptions": {k: v for k, v in self.assumptions},
                "governance_summary": self.governance_summary, "parents": list(self.parents),
                "context_version": self.context_version, "signature": self.signature()}


# --- scenario record (frozen) -------------------------------------------------
@dataclass(frozen=True)
class ScenarioRecord:
    scenario_id: str
    scenario_type: str
    name: str
    context: ScenarioContext
    description: str = ""
    version: str = ""
    previous_version: Optional[str] = None
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    created_at: str = DETERMINISTIC_EPOCH
    domain_version: str = SIMULATION_DOMAIN_VERSION

    def version_previous(self) -> Optional[str]:
        return self.previous_version

    def state_signature(self) -> str:
        return hash_obj({"scenario_id": self.scenario_id, "scenario_type": self.scenario_type,
                         "name": self.name, "context": self.context.signature(),
                         "description": self.description})

    def to_dict(self) -> dict:
        return {"scenario_id": self.scenario_id, "scenario_type": self.scenario_type,
                "name": self.name, "description": self.description,
                "context": self.context.to_dict(), "version": self.version,
                "lineage_id": self.lineage_id, "audit_state": self.audit_state,
                "created_at": self.created_at, "domain_version": self.domain_version,
                "state_signature": self.state_signature()}


# --- simulation outcome (per dimension) --------------------------------------
@dataclass(frozen=True)
class SimulationOutcome:
    dimension: str
    status: str                          # ready | degraded | blocked
    score: float                         # [0,1] deterministic readiness for this dimension
    detail: str
    metrics: dict

    def state_signature(self) -> str:
        return hash_obj({"dimension": self.dimension, "status": self.status,
                         "score": self.score, "metrics": self.metrics})

    def to_dict(self) -> dict:
        return {"dimension": self.dimension, "status": self.status, "score": self.score,
                "detail": self.detail, "metrics": self.metrics}


# --- forecast record ----------------------------------------------------------
@dataclass(frozen=True)
class ForecastRecord:
    forecast_id: str
    forecast_type: str
    projected_status: str
    confidence: float                    # explainable [0,1] (derived ratio, not random)
    factors: tuple[str, ...]
    explanation: str
    forecast_version: str = SIMULATION_FORECAST_VERSION

    def state_signature(self) -> str:
        return hash_obj({"forecast_type": self.forecast_type,
                         "projected_status": self.projected_status,
                         "confidence": self.confidence, "factors": list(self.factors)})

    def to_dict(self) -> dict:
        return {"forecast_id": self.forecast_id, "forecast_type": self.forecast_type,
                "projected_status": self.projected_status, "confidence": self.confidence,
                "factors": list(self.factors), "explanation": self.explanation,
                "forecast_version": self.forecast_version}


# --- simulation risk record ---------------------------------------------------
@dataclass(frozen=True)
class SimulationRiskRecord:
    risk_id: str
    dimension: str
    score: float                         # explainable [0,1]
    level: str
    factors: tuple[str, ...]
    explanation: str
    risk_version: str = SIMULATION_RISK_VERSION

    def state_signature(self) -> str:
        return hash_obj({"dimension": self.dimension, "score": self.score, "level": self.level,
                         "factors": list(self.factors)})

    def to_dict(self) -> dict:
        return {"risk_id": self.risk_id, "dimension": self.dimension, "score": self.score,
                "level": self.level, "factors": list(self.factors),
                "explanation": self.explanation, "risk_version": self.risk_version}


# --- simulation result (aggregate of one run) --------------------------------
@dataclass(frozen=True)
class SimulationResult:
    outcomes: tuple = ()                 # tuple[SimulationOutcome]
    forecasts: tuple = ()                # tuple[ForecastRecord]
    risks: tuple = ()                    # tuple[SimulationRiskRecord]
    readiness_score: float = 0.0
    readiness_status: str = OutcomeStatus.BLOCKED
    summary: str = ""

    def state_signature(self) -> str:
        return hash_obj({
            "outcomes": [o.state_signature() for o in self.outcomes],
            "forecasts": [f.state_signature() for f in self.forecasts],
            "risks": [r.state_signature() for r in self.risks],
            "readiness_score": self.readiness_score, "readiness_status": self.readiness_status})

    def to_dict(self) -> dict:
        return {"outcomes": [o.to_dict() for o in self.outcomes],
                "forecasts": [f.to_dict() for f in self.forecasts],
                "risks": [r.to_dict() for r in self.risks],
                "readiness_score": self.readiness_score,
                "readiness_status": self.readiness_status, "summary": self.summary}


# --- simulation record (frozen) ----------------------------------------------
@dataclass(frozen=True)
class SimulationRecord:
    simulation_id: str
    scenario_id: str
    scenario_type: str
    result: SimulationResult
    version: str = ""
    previous_version: Optional[str] = None
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    created_at: str = DETERMINISTIC_EPOCH
    domain_version: str = SIMULATION_DOMAIN_VERSION

    def version_previous(self) -> Optional[str]:
        return self.previous_version

    @property
    def forecasts(self) -> tuple:
        return self.result.forecasts

    @property
    def risks(self) -> tuple:
        return self.result.risks

    def state_signature(self) -> str:
        return hash_obj({"simulation_id": self.simulation_id, "scenario_id": self.scenario_id,
                         "scenario_type": self.scenario_type,
                         "result": self.result.state_signature()})

    def to_dict(self) -> dict:
        return {"simulation_id": self.simulation_id, "scenario_id": self.scenario_id,
                "scenario_type": self.scenario_type, "result": self.result.to_dict(),
                "version": self.version, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state, "created_at": self.created_at,
                "domain_version": self.domain_version, "state_signature": self.state_signature()}


# --- comparison record --------------------------------------------------------
@dataclass(frozen=True)
class ComparisonRecord:
    comparison_id: str
    scenario_ids: tuple
    simulation_ids: tuple
    advantages: tuple                    # tuple[dict]
    risks: tuple                         # tuple[dict]
    tradeoffs: tuple                     # tuple[str]
    governance_impact: dict
    constraint_impact: dict
    recommended_scenario_id: str
    explanation: str = ""
    version: str = ""
    previous_version: Optional[str] = None
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    created_at: str = DETERMINISTIC_EPOCH
    comparison_version: str = SIMULATION_COMPARISON_VERSION

    def version_previous(self) -> Optional[str]:
        return self.previous_version

    def state_signature(self) -> str:
        return hash_obj({"scenario_ids": list(self.scenario_ids),
                         "simulation_ids": list(self.simulation_ids),
                         "advantages": list(self.advantages), "risks": list(self.risks),
                         "tradeoffs": list(self.tradeoffs),
                         "governance_impact": self.governance_impact,
                         "constraint_impact": self.constraint_impact,
                         "recommended_scenario_id": self.recommended_scenario_id})

    def to_dict(self) -> dict:
        return {"comparison_id": self.comparison_id, "scenario_ids": list(self.scenario_ids),
                "simulation_ids": list(self.simulation_ids), "advantages": list(self.advantages),
                "risks": list(self.risks), "tradeoffs": list(self.tradeoffs),
                "governance_impact": self.governance_impact,
                "constraint_impact": self.constraint_impact,
                "recommended_scenario_id": self.recommended_scenario_id,
                "explanation": self.explanation, "version": self.version,
                "lineage_id": self.lineage_id, "audit_state": self.audit_state,
                "created_at": self.created_at, "comparison_version": self.comparison_version,
                "state_signature": self.state_signature()}


# --- version ------------------------------------------------------------------
@dataclass(frozen=True)
class SimulationVersion:
    version: str
    previous: Optional[str]
    reason: str
    created_at: str = DETERMINISTIC_EPOCH

    @staticmethod
    def compute(state_signature: str, previous: Optional[str]) -> str:
        return hash_obj({"state": state_signature, "previous": previous})

    def to_dict(self) -> dict:
        return {"version": self.version, "previous": self.previous, "reason": self.reason,
                "created_at": self.created_at}


# --- audit record -------------------------------------------------------------
@dataclass(frozen=True)
class SimulationAuditRecord:
    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {"seq": self.seq, "kind": self.kind, "payload": self.payload,
                "prev_hash": self.prev_hash, "event_hash": self.event_hash,
                "created_at": self.created_at}


# --- lineage projection -------------------------------------------------------
@dataclass(frozen=True)
class SimulationLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


# --- registry record ----------------------------------------------------------
@dataclass
class SimulationRegistryRecord:
    artifact_id: str
    artifact_kind: str                   # scenario | simulation | comparison
    version: str
    lineage_id: str
    audit_state: str
    content_signature_value: str
    simulation_registry_version: str = SIMULATION_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"artifact_id": self.artifact_id, "artifact_kind": self.artifact_kind,
                         "version": self.version, "lineage_id": self.lineage_id,
                         "content": self.content_signature_value})

    def to_dict(self) -> dict:
        return {"artifact_id": self.artifact_id, "artifact_kind": self.artifact_kind,
                "version": self.version, "lineage_id": self.lineage_id,
                "audit_state": self.audit_state,
                "content_signature_value": self.content_signature_value,
                "simulation_registry_version": self.simulation_registry_version,
                "content_signature": self.content_signature()}
