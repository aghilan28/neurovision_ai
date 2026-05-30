"""Simulation lineage helpers built on ml.lineage.

Every scenario, simulation, and comparison gets a content-addressed lineage node whose
parents are the lineage nodes of the governed artifacts it evaluated (goals, policies,
constraints, plans, tasks, agents, executions, governance intelligence) — and, for a
simulation, the scenario node; for a comparison, the simulation nodes. Because those
parents trace through their own chains to the patient, ``verify_chain`` from a
simulation artifact spans Patient -> ... -> Execution -> Governance Intelligence ->
Scenario -> Simulation.

Shares the platform's single ``ml.lineage.LineageTracker`` — no parallel lineage.
"""

from __future__ import annotations

from typing import Sequence

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    SIMULATION_SCENARIO_VERSION, SIMULATION_DOMAIN_VERSION, SIMULATION_IDENTITY_VERSION,
    SIMULATION_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def simulation_version_bundle(**extra: object) -> dict:
    bundle = {
        "simulation_scenario_version": SIMULATION_SCENARIO_VERSION,
        "simulation_domain_version": SIMULATION_DOMAIN_VERSION,
        "simulation_identity_version": SIMULATION_IDENTITY_VERSION,
        "simulation_lineage_version": SIMULATION_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_simulation_lineage(artifact_id: str, *, kind: str, parents: Sequence[str] = (),
                            reason: str = "created", created_at: str = DETERMINISTIC_EPOCH,
                            extra: dict | None = None) -> LineageRecord:
    """A simulation lineage node (kind in scenario|simulation|comparison) parented by
    the evaluated artifacts' nodes."""
    outputs = {"artifact_id": artifact_id, "reason": reason}
    if extra:
        outputs.update(extra)
    return make_lineage_record(
        kind=kind, versions=simulation_version_bundle(),
        inputs={"artifact_id": artifact_id, "n_parents": len(tuple(parents))},
        outputs=outputs, parents=tuple(p for p in parents if p), created_at=created_at)


__all__ = ["simulation_version_bundle", "make_simulation_lineage"]
