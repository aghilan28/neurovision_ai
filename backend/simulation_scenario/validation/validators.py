"""Simulation validation — the mandated integrity checks (V4-P9).

``SimulationValidator`` verifies a registered simulation (and its scenario, and an
optional comparison) across the mandated dimensions: scenario, simulation, forecast,
comparison, registry, audit, lineage, and version integrity. Reuses the shared
``ml.validation.ValidationReport``.
"""

from __future__ import annotations

from typing import Any, Optional

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import (
    validate_scenario_identity, validate_simulation_identity, validate_forecast_identity,
    validate_comparison_identity, validate_risk_identity,
)
from ..models.domain import (
    SimulationRecord, ScenarioRecord, ComparisonRecord, SimulationVersion, SCENARIO_TYPES,
    FORECAST_TYPES, SIM_RISK_DIMENSIONS,
)


class SimulationValidator:
    """Validates integrity of a registered simulation artifact."""

    def validate(self, *, simulation: SimulationRecord, scenario: ScenarioRecord, registry: Any,
                 audit_log: Any, lineage_tracker: Any,
                 comparison: Optional[ComparisonRecord] = None) -> ValidationReport:
        report = ValidationReport()
        result = simulation.result

        # 1. scenario integrity
        scenario_ok = (validate_scenario_identity(scenario.scenario_id)[0]
                       and scenario.scenario_type in SCENARIO_TYPES
                       and bool(scenario.context.signature()))
        report.add("scenario_integrity", bool(scenario_ok),
                   f"scenario_id={scenario.scenario_id} type={scenario.scenario_type}")

        # 2. simulation integrity
        sim_ok = (validate_simulation_identity(simulation.simulation_id)[0]
                  and simulation.scenario_id == scenario.scenario_id
                  and bool(result.outcomes) and 0.0 <= result.readiness_score <= 1.0)
        report.add("simulation_integrity", bool(sim_ok),
                   f"readiness={result.readiness_score} n_outcomes={len(result.outcomes)}")

        # 3. forecast integrity
        fc_ok = all(validate_forecast_identity(f.forecast_id)[0]
                    and f.forecast_type in FORECAST_TYPES and 0.0 <= f.confidence <= 1.0
                    and f.factors and f.explanation for f in result.forecasts)
        report.add("forecast_integrity", bool(fc_ok), f"{len(result.forecasts)} forecast(s)")

        # 3b. risk integrity (part of simulation integrity surface)
        risk_ok = all(validate_risk_identity(r.risk_id)[0] and r.dimension in SIM_RISK_DIMENSIONS
                      and 0.0 <= r.score <= 1.0 and r.factors for r in result.risks)
        report.add("risk_integrity", bool(risk_ok), f"{len(result.risks)} risk(s)")

        # 4. comparison integrity (vacuously true when no comparison in scope)
        if comparison is None:
            report.add("comparison_integrity", True, "no comparison in scope")
        else:
            comp_ok = (validate_comparison_identity(comparison.comparison_id)[0]
                       and len(comparison.scenario_ids) >= 2
                       and comparison.recommended_scenario_id in comparison.scenario_ids)
            report.add("comparison_integrity", bool(comp_ok),
                       f"recommended={comparison.recommended_scenario_id}")

        # 5. registry integrity
        try:
            rec = registry.get(simulation.simulation_id)
            ok = rec.version == simulation.version and rec.lineage_id == simulation.lineage_id
            report.add("registry_integrity", bool(ok),
                       f"registered version={rec.version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        # 6. audit integrity
        try:
            heads = {e.event_hash for e in audit_log.events()}
            ok = audit_log.verify() and (simulation.audit_state in heads)
            report.add("audit_integrity", bool(ok), f"chain_verified={audit_log.verify()}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # 7. lineage integrity
        try:
            chain_ok = bool(simulation.lineage_id) and lineage_tracker.verify_chain(
                simulation.lineage_id)
            report.add("lineage_integrity", bool(chain_ok), f"chain_ok={chain_ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # 8. version integrity
        try:
            expected = SimulationVersion.compute(simulation.state_signature(),
                                                 simulation.version_previous())
            report.add("version_integrity", simulation.version == expected,
                       f"recorded={simulation.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        return report
