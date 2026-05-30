"""Workflow builder (V3-P3) — assembles a WorkflowRecord from events.

Combines the transition engine, dependency engine, bottleneck analysis, and
efficiency analytics into one derived :class:`WorkflowRecord`. Everything is read
from the recorded events (via the temporal ``EventSourceView``) plus optional
entity refs for dependencies — no hidden workflow state.
"""

from __future__ import annotations

from typing import Optional, Sequence

from ..identity import mint_workflow
from ..models.domain import WorkflowRecord, WorkflowMetadata
from ..transitions import derive_transitions
from ..dependencies import EntityRef, derive_dependencies
from ..bottlenecks import detect as detect_bottlenecks
from ..efficiency import compute as compute_efficiency


class WorkflowBuilder:
    """Builds :class:`WorkflowRecord` artifacts from events (read-only)."""

    def build(self, *, workflow_type: str, subject_kind: str, subject_id: str,
              events: Sequence, dependency_refs: Optional[Sequence[EntityRef]] = None) -> WorkflowRecord:
        transitions = derive_transitions(events)
        dependencies = derive_dependencies(dependency_refs or [])
        total_events = len(events)

        bottleneck_metrics, detected = detect_bottlenecks(
            transitions, dependencies, total_events=total_events)
        n_rework = int(next((m.value for m in bottleneck_metrics if m.name == "rework_states"), 0))
        n_slow = int(next((m.value for m in bottleneck_metrics if m.name == "slow_transitions"), 0))
        efficiency_metrics = compute_efficiency(
            transitions, total_events=total_events, n_rework_states=n_rework, n_slow=n_slow)

        metrics = tuple(bottleneck_metrics + efficiency_metrics)
        state = transitions[-1].to_state if transitions else "empty"
        metadata = WorkflowMetadata(
            source_event_ids=tuple(e.event_id for e in events),
            n_events=total_events, bottlenecks=tuple(detected))

        ident = mint_workflow(workflow_type, subject_id)
        return WorkflowRecord(
            workflow_id=ident.id, workflow_type=workflow_type, subject_kind=subject_kind,
            subject_id=subject_id, state=state, transitions=tuple(transitions),
            dependencies=tuple(dependencies), metrics=metrics, metadata=metadata)
