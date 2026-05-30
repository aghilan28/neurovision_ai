"""The simulation registry (V4-P9).

Tracks every admitted scenario, simulation, and comparison (by id + version) plus flat
indexes of the forecasts and risks they produced — so reports can look them up without
recomputation. No artifact may exist outside the registry; re-registering the same
id + version with different content is a forbidden silent overwrite.
"""

from __future__ import annotations

from ..version import SIMULATION_REGISTRY_VERSION
from ..models.domain import SimulationRegistryRecord


class SimulationRegistry:
    """In-memory registry keyed by artifact id (+ flattened forecast/risk indexes)."""

    def __init__(self) -> None:
        self._records: dict[str, SimulationRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}
        self._scenarios: dict[str, dict] = {}
        self._simulations: dict[str, dict] = {}
        self._comparisons: dict[str, dict] = {}
        self._forecasts: dict[str, dict] = {}
        self._risks: dict[str, dict] = {}

    def register(self, record: SimulationRegistryRecord) -> SimulationRegistryRecord:
        key = (record.artifact_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"simulation artifact {record.artifact_id} version {record.version} already "
                "registered with different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.artifact_id] = record
        return record

    def index_scenario(self, scenario) -> None:
        self._scenarios[scenario.scenario_id] = scenario.to_dict()

    def index_simulation(self, simulation) -> None:
        self._simulations[simulation.simulation_id] = simulation.to_dict()
        for f in simulation.result.forecasts:
            self._forecasts[f.forecast_id] = f.to_dict()
        for r in simulation.result.risks:
            self._risks[r.risk_id] = r.to_dict()

    def index_comparison(self, comparison) -> None:
        self._comparisons[comparison.comparison_id] = comparison.to_dict()

    def get(self, artifact_id: str) -> SimulationRegistryRecord:
        if artifact_id not in self._records:
            raise KeyError(f"simulation artifact {artifact_id!r} not in registry")
        return self._records[artifact_id]

    def exists(self, artifact_id: str) -> bool:
        return artifact_id in self._records

    def list_scenarios(self) -> list:
        return sorted(self._scenarios)

    def list_simulations(self) -> list:
        return sorted(self._simulations)

    def list_comparisons(self) -> list:
        return sorted(self._comparisons)

    def list_forecasts(self) -> list:
        return sorted(self._forecasts)

    def list_risks(self) -> list:
        return sorted(self._risks)

    def to_dict(self) -> dict:
        return {"simulation_registry_version": SIMULATION_REGISTRY_VERSION,
                "n_artifacts": len(self._records), "n_scenarios": len(self._scenarios),
                "n_simulations": len(self._simulations), "n_comparisons": len(self._comparisons),
                "n_forecasts": len(self._forecasts), "n_risks": len(self._risks),
                "artifacts": {aid: r.to_dict() for aid, r in sorted(self._records.items())},
                "scenarios": dict(sorted(self._scenarios.items())),
                "simulations": dict(sorted(self._simulations.items())),
                "comparisons": dict(sorted(self._comparisons.items()))}
