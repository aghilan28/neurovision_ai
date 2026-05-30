"""Efficiency analytics (V3-P3).

Computes deterministic efficiency metrics from a workflow's transitions: completion
rate, transition durations (in logical steps), rework rate, throughput, operational
velocity, and a composite workflow health score in [0, 1]. All are reproducible
ratios/counts over already-derived inputs (no wall-clock).
"""

from __future__ import annotations

from typing import Sequence

from ..models.domain import WorkflowMetric, WorkflowTransition

# Terminal states per workflow type that count as "completed".
_COMPLETED_STATES = {"reviewed", "completed", "confirmed", "closed", "archived"}


def _round(x: float) -> float:
    r = round(float(x), 6)
    return 0.0 if r == 0 else r


def compute(transitions: Sequence[WorkflowTransition], *, total_events: int,
            n_rework_states: int, n_slow: int) -> list[WorkflowMetric]:
    n_tr = len(transitions)
    reached_states = [t.to_state for t in transitions]
    completed = any(s in _COMPLETED_STATES for s in reached_states)

    metrics: list[WorkflowMetric] = []

    # completion rate: 1.0 if a completed terminal state was reached, else 0.0.
    metrics.append(WorkflowMetric("completion_rate", 1.0 if completed else 0.0, "ratio",
                                  n_tr > 0, "reached a terminal completed state"))

    # mean transition duration in logical steps (order gap between transitions).
    if n_tr > 1:
        gaps = [cur.order - prev.order for prev, cur in zip(transitions, transitions[1:])]
        mean_gap = _round(sum(gaps) / len(gaps))
    else:
        mean_gap = 0.0
    metrics.append(WorkflowMetric("mean_transition_steps", mean_gap, "logical_steps",
                                  n_tr > 1, "mean logical-step gap between transitions"))

    # rework rate: fraction of transitions that are re-entries.
    rework_rate = _round(n_rework_states / n_tr) if n_tr else 0.0
    metrics.append(WorkflowMetric("rework_rate", rework_rate, "ratio", n_tr > 0,
                                  "fraction of states re-entered"))

    # throughput: transitions per recorded event (work done per observation).
    throughput = _round(n_tr / total_events) if total_events else 0.0
    metrics.append(WorkflowMetric("throughput", throughput, "ratio", total_events > 0,
                                  "transitions per recorded event"))

    # operational velocity: transitions per logical step span.
    span = (transitions[-1].order - transitions[0].order + 1) if n_tr else 0
    velocity = _round(n_tr / span) if span else 0.0
    metrics.append(WorkflowMetric("operational_velocity", velocity, "ratio", n_tr > 0,
                                  "transitions per logical-step span"))

    # composite health score: rewards completion + velocity, penalizes rework + stalls.
    health = 0.0
    if n_tr > 0:
        health = (0.5 * (1.0 if completed else 0.0)
                  + 0.2 * min(1.0, velocity)
                  + 0.2 * (1.0 - min(1.0, rework_rate))
                  + 0.1 * (1.0 - min(1.0, n_slow / max(1, n_tr))))
    metrics.append(WorkflowMetric("workflow_health_score", _round(health), "ratio", n_tr > 0,
                                  "composite of completion/velocity/rework/slowness"))
    return metrics
