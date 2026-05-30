"""Bottleneck analysis (V3-P3).

Detects bottleneck conditions deterministically from a workflow's transitions and
dependencies. "Slow" is measured in logical steps (the platform forbids wall-clock),
so a slow transition is one whose logical-step gap exceeds a fixed threshold. All
detectors are pure functions over already-derived workflow inputs.
"""

from __future__ import annotations

from typing import Sequence

from ..models.domain import WorkflowMetric, WorkflowTransition, WorkflowDependency

# A transition spanning more than this many logical steps (events between two
# state changes) is flagged "slow".
SLOW_STEP_THRESHOLD = 4
# More than this many transitions into the same state == rework.
REWORK_THRESHOLD = 1


def detect(transitions: Sequence[WorkflowTransition], dependencies: Sequence[WorkflowDependency],
           *, total_events: int) -> tuple[list[WorkflowMetric], list[str]]:
    """Return (bottleneck metrics, list of detected bottleneck condition names)."""
    metrics: list[WorkflowMetric] = []
    detected: list[str] = []

    # 1. slow transitions: logical-step gap between consecutive transition events.
    #    The gap is the difference in transition order vs. event ordinal is not
    #    available here; we use the number of transitions as the step budget and
    #    flag stalls when a workflow has events but very few transitions.
    n_tr = len(transitions)
    slow = 0
    for prev, cur in zip(transitions, transitions[1:]):
        if (cur.order - prev.order) > SLOW_STEP_THRESHOLD:
            slow += 1
    metrics.append(WorkflowMetric("slow_transitions", float(slow), "count", n_tr > 1,
                                  f"transitions spanning > {SLOW_STEP_THRESHOLD} steps"))
    if slow > 0:
        detected.append("slow_transitions")

    # 2. repeated rework: the same to_state reached more than once.
    to_counts: dict = {}
    for t in transitions:
        to_counts[t.to_state] = to_counts.get(t.to_state, 0) + 1
    rework_states = sorted(s for s, c in to_counts.items() if c > REWORK_THRESHOLD)
    metrics.append(WorkflowMetric("rework_states", float(len(rework_states)), "count", n_tr > 0,
                                  f"states re-entered > {REWORK_THRESHOLD} time(s): {rework_states}"))
    if rework_states:
        detected.append("repeated_rework")

    # 3. workflow stall: events recorded but no (or one) transition produced.
    stalled = total_events > 0 and n_tr <= 1
    metrics.append(WorkflowMetric("workflow_stall", 1.0 if stalled else 0.0, "ratio", total_events > 0,
                                  "events present but <=1 transition"))
    if stalled:
        detected.append("workflow_stall")

    # 4. excessive wait states: dependencies in 'waiting' or 'blocked'.
    waits = sum(1 for d in dependencies if d.relation in ("waiting", "blocked"))
    metrics.append(WorkflowMetric("wait_states", float(waits), "count", bool(dependencies),
                                  "dependencies in waiting/blocked"))
    if waits > 0:
        detected.append("excessive_wait_states")

    # 5. dependency congestion: an entity depended on by multiple others.
    indegree: dict = {}
    for d in dependencies:
        if d.relation in ("downstream", "blocked", "completed"):
            indegree[d.from_entity] = indegree.get(d.from_entity, 0) + 1
    congested = sorted(e for e, c in indegree.items() if c > 2)
    metrics.append(WorkflowMetric("dependency_congestion", float(len(congested)), "count",
                                  bool(dependencies), f"entities with >2 dependents: {len(congested)}"))
    if congested:
        detected.append("dependency_congestion")

    return metrics, detected
