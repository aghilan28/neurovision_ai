"""Scenario context construction (V4-P9) — the read-only source view.

A simulation evaluates a *snapshot* of the already-governed artifacts. To avoid a
parallel observation system, this module **reuses** the V4-P7 Governance Intelligence
``GovernanceObservationView`` to normalize goals / policies / constraints / plans /
tasks / agents / executions into uniform observations, and assembles a frozen,
content-addressed :class:`ScenarioContext` (observations + governance summary +
declarative what-if assumptions). Reading only — production state is never touched.
"""

from __future__ import annotations

import json
from typing import Sequence

from backend.governance_intelligence import (  # sibling reuse (no cycle)
    GovernanceObservationView, GovernedObservation,
)

from .domain import ScenarioContext


class SimulationView:
    """A read-only snapshot of the governed artifacts a simulation may evaluate."""

    def __init__(self, obs_view: GovernanceObservationView, governance_summary: dict,
                 extra_parents: Sequence = ()):
        self._obs = obs_view
        self.governance_summary = dict(governance_summary)
        # additional lineage parents to weave into the chain — e.g. the V4-P7
        # governance-intelligence node, so the deliverable chain reads
        # ... -> Governance Intelligence -> Simulation.
        self._extra_parents = tuple(p for p in extra_parents if p)

    @classmethod
    def from_sources(cls, *, goals: Sequence = (), policies: Sequence = (),
                     constraints: Sequence = (), plans: Sequence = (), tasks: Sequence = (),
                     agents: Sequence = (), executions: Sequence = (),
                     governance_summary: dict | None = None,
                     extra_parents: Sequence = ()) -> "SimulationView":
        view = GovernanceObservationView.from_sources(
            goals=goals, policies=policies, constraints=constraints, plans=plans, tasks=tasks,
            agents=agents, executions=executions)
        return cls(view, governance_summary or {}, extra_parents=extra_parents)

    def observations(self) -> list:
        return self._obs.all()

    def by_kind(self, kind: str) -> list:
        return self._obs.by_kind(kind)

    def parents(self) -> tuple:
        seen: list = []
        for p in (*self._obs.parents(), *self._extra_parents):
            if p and p not in seen:
                seen.append(p)
        return tuple(seen)

    def kinds(self) -> tuple:
        return self._obs.kinds()


def _normalise_assumptions(assumptions: dict | None) -> tuple:
    """Canonicalize assumptions to a sorted tuple of (key, json-value) pairs."""
    if not assumptions:
        return ()
    return tuple(sorted((str(k), json.dumps(v, sort_keys=True)) for k, v in assumptions.items()))


def build_context(view: SimulationView, *, focus_kind: str,
                  assumptions: dict | None = None) -> ScenarioContext:
    """Assemble a reproducible :class:`ScenarioContext` from a :class:`SimulationView`."""
    observations = tuple(o.to_dict() for o in view.observations())
    return ScenarioContext(
        focus_kind=focus_kind, observations=observations,
        assumptions=_normalise_assumptions(assumptions),
        governance_summary=dict(view.governance_summary), parents=view.parents())


def observations_from_context(context: ScenarioContext) -> list:
    """Rehydrate :class:`GovernedObservation`s from a context (deterministic, read-only)."""
    out = []
    for d in context.observations:
        out.append(GovernedObservation(
            kind=d["kind"], entity_id=d["entity_id"], approval_state=d["approval_state"],
            decision=d.get("decision", ""), authority=d.get("authority"),
            history=tuple(d.get("history", ())),
            escalation_required=bool(d.get("escalation_required", False)),
            escalated=bool(d.get("escalated", False)),
            policy_references=tuple(d.get("policy_references", ())), state=d.get("state", ""),
            lineage_id=d.get("lineage_id"), live=bool(d.get("live", False))))
    return out
