"""Simulation governance gate (V4-P9).

The architecture/quality/context/risk/governance gate every simulation artifact must
pass before admission. Reuses the shared ``ml.validation.ValidationReport`` — no
parallel governance system.

The defining invariant is **evaluate, never execute**: the simulation layer may
observe and evaluate possible futures, but must never execute, authorize, commit, or
deploy anything. The gate encodes that invariant (risk + governance dimensions reject
any artifact whose statuses claim a real action was taken).

Dimensions:
  * architecture — known scenario type; observed kinds are governed kinds.
  * quality      — deterministic + explainable: readiness in [0,1]; every forecast has
                   factors + explanation; every risk score in [0,1] and explained.
  * context      — has lineage parents (traceable to the governed artifacts) when
                   required, so the artifact traces back to the patient.
  * risk         — risk scores in [0,1] (bounded, explainable).
  * governance   — observe/evaluate-only: no outcome/forecast status claims a real
                   action (executed/authorized/committed/deployed/running).
"""

from __future__ import annotations

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..models.domain import (
    SCENARIO_TYPES, SimulationRecord, ScenarioRecord, ComparisonRecord, OutcomeStatus,
)

# statuses that would mean a real action occurred — forbidden in an evaluation layer.
_ACTION_STATUSES = frozenset({"executed", "authorized", "committed", "deployed", "running",
                              "applied", "mutated"})
_VALID_OUTCOME = frozenset({OutcomeStatus.READY, OutcomeStatus.DEGRADED, OutcomeStatus.BLOCKED})


class SimulationGovernanceError(RuntimeError):
    """Raised when the simulation governance gate rejects an artifact."""


class SimulationGate:
    """The five-dimension gate for simulation artifacts (reuses ValidationReport)."""

    def evaluate_scenario(self, *, scenario: ScenarioRecord, parents: tuple = (),
                          requires_lineage: bool = True) -> ValidationReport:
        report = ValidationReport()
        report.add("architecture_validation", scenario.scenario_type in SCENARIO_TYPES,
                   f"scenario_type={scenario.scenario_type}")
        report.add("quality_validation", bool(scenario.name) and bool(scenario.context.signature()),
                   "named + content-addressed context")
        report.add("context_validation", (not requires_lineage) or len(parents) > 0,
                   f"{len(parents)} lineage parent(s)")
        report.add("risk_validation", True, "scenario is a hypothesis; carries no risk payload")
        report.add("governance_validation", True,
                   "scenario observes/evaluates only; no action payload")
        return report

    def evaluate_simulation(self, *, simulation: SimulationRecord, parents: tuple = (),
                            requires_lineage: bool = True) -> ValidationReport:
        report = ValidationReport()
        result = simulation.result

        report.add("architecture_validation", simulation.scenario_type in SCENARIO_TYPES,
                   f"scenario_type={simulation.scenario_type}")

        outcomes_ok = all(o.status in _VALID_OUTCOME and 0.0 <= o.score <= 1.0
                          for o in result.outcomes)
        forecasts_ok = all(f.factors and f.explanation and 0.0 <= f.confidence <= 1.0
                           for f in result.forecasts)
        quality_ok = (0.0 <= result.readiness_score <= 1.0 and bool(result.outcomes)
                      and outcomes_ok and forecasts_ok)
        report.add("quality_validation", quality_ok,
                   "deterministic readiness + explainable forecasts" if quality_ok
                   else "bad readiness / non-explainable forecast / invalid outcome")

        report.add("context_validation", (not requires_lineage) or len(parents) > 0,
                   f"{len(parents)} lineage parent(s)")

        risk_ok = all(0.0 <= r.score <= 1.0 and r.factors for r in result.risks)
        report.add("risk_validation", risk_ok, "risk scores bounded + explainable")

        # observe-only: no status anywhere claims a real action occurred.
        action_free = (all(o.status not in _ACTION_STATUSES for o in result.outcomes)
                       and all(f.projected_status not in _ACTION_STATUSES
                               for f in result.forecasts))
        report.add("governance_validation", action_free,
                   "evaluation only; no executed/authorized/committed payload" if action_free
                   else "artifact claims a real action (forbidden in simulation)")
        return report

    def evaluate_comparison(self, *, comparison: ComparisonRecord, parents: tuple = (),
                            requires_lineage: bool = True) -> ValidationReport:
        report = ValidationReport()
        report.add("architecture_validation", len(comparison.scenario_ids) >= 2,
                   f"{len(comparison.scenario_ids)} scenarios compared")
        report.add("quality_validation",
                   bool(comparison.recommended_scenario_id) and bool(comparison.explanation),
                   "has a justified recommendation")
        report.add("context_validation", (not requires_lineage) or len(parents) > 0,
                   f"{len(parents)} lineage parent(s)")
        report.add("risk_validation", isinstance(comparison.risks, tuple),
                   "per-scenario risks enumerated")
        report.add("governance_validation",
                   comparison.recommended_scenario_id in comparison.scenario_ids,
                   "recommends only a compared scenario; recommends, never executes")
        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise SimulationGovernanceError(f"simulation gate rejected: {names}")
