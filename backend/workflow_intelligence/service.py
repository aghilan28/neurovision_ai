"""WorkflowIntelligenceService — the governed orchestration hub for V3-P3.

Derives **workflows** (first-class entities) from events (V3-P1) and temporal
intelligence (V3-P2), and admits each through one governed path: governance gate
(architecture/quality/context/risk) → shared-lineage node parented by the **event**
lineage nodes it derives from (optionally the source **timeline** node) → immutable
audit event → content-addressed version → registry sync.

Because each workflow's lineage parents are event/timeline nodes (which trace to the
patient), a single ``verify_chain`` spans Patient → ... → Event → (Timeline) →
Workflow. No hidden workflow state: everything is read from the recorded events via
the temporal :class:`EventSourceView`. Shares the platform's single
``ml.lineage.LineageTracker``.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional, Sequence

from ml.lineage import LineageTracker  # allowed: backend -> ml
from backend.temporal_intelligence.timelines import EventSourceView

from .version import DETERMINISTIC_EPOCH
from .analytics import WorkflowBuilder
from .dependencies import EntityRef
from .models.domain import WorkflowVersion, WorkflowRegistryRecord
from .audit import make_workflow_audit_log
from .lineage import make_workflow_lineage
from .registry import WorkflowRegistry
from .validation import WorkflowGovernanceGate, WorkflowValidator
from .reports import (
    build_workflow_report, build_transition_report, build_dependency_report,
    build_bottleneck_report, build_efficiency_report, build_validation_report, build_audit_report,
)


class WorkflowIntelligenceService:
    """Stateful service: workflow registry, shared lineage tracker, immutable audit log."""

    def __init__(self, event_service, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[WorkflowRegistry] = None):
        # event_service: backend.operational_events.OperationalEventService
        self.events = event_service
        self.lineage = lineage_tracker or event_service.lineage
        self.registry = registry or WorkflowRegistry()
        self.audit = make_workflow_audit_log()
        self.gate = WorkflowGovernanceGate()
        self.validator = WorkflowValidator()
        self._builder = WorkflowBuilder()
        self._view: Optional[EventSourceView] = None

    # --- event source view ----------------------------------------------------
    def load_events(self, events: Sequence) -> "WorkflowIntelligenceService":
        """Provide the recorded EventRecord objects to derive workflows from."""
        self._view = EventSourceView(events)
        return self

    def view(self) -> EventSourceView:
        if self._view is None:
            raise RuntimeError("call load_events(...) before deriving workflows")
        return self._view

    def _event_parents(self, events: Sequence) -> tuple:
        return tuple(e.lineage_id for e in events if getattr(e, "lineage_id", None))

    # --- build ----------------------------------------------------------------
    def build_workflow(self, *, workflow_type: str, subject_kind: str, subject_id: str,
                       source_entity_ids: Sequence[str],
                       dependency_refs: Optional[Sequence[EntityRef]] = None,
                       extra_parents: Sequence[str] = (),
                       created_at: str = DETERMINISTIC_EPOCH):
        view = self.view()
        events = view.for_sources(source_entity_ids)
        workflow = self._builder.build(workflow_type=workflow_type, subject_kind=subject_kind,
                                       subject_id=subject_id, events=events,
                                       dependency_refs=dependency_refs)
        parents = self._event_parents(events) + tuple(extra_parents)
        return self._finalize(workflow, parents, reason="workflow_built", created_at=created_at)

    def build_operational_workflow(self, *, extra_parents: Sequence[str] = (),
                                   created_at: str = DETERMINISTIC_EPOCH):
        """A platform-wide workflow over every event (operational behavior)."""
        view = self.view()
        events = view.all()
        workflow = self._builder.build(workflow_type="operational_workflow",
                                       subject_kind="operational", subject_id="all",
                                       events=events, dependency_refs=None)
        parents = self._event_parents(events) + tuple(extra_parents)
        return self._finalize(workflow, parents, reason="operational_workflow_built",
                              created_at=created_at)

    # --- validation + reports -------------------------------------------------
    def validate(self, workflow):
        return self.validator.validate(workflow=workflow, registry=self.registry,
                                       audit_log=self.audit, lineage_tracker=self.lineage)

    def reports(self, workflow) -> dict:
        return {
            "workflow_report": build_workflow_report(workflow),
            "transition_report": build_transition_report(workflow),
            "dependency_report": build_dependency_report(workflow),
            "bottleneck_report": build_bottleneck_report(workflow),
            "efficiency_report": build_efficiency_report(workflow),
            "audit_report": build_audit_report(self.audit),
        }

    def validation_report(self, scope: str, validation_report_dict: dict) -> dict:
        return build_validation_report(scope, validation_report_dict)

    # --- internals ------------------------------------------------------------
    def _finalize(self, workflow, parents: tuple, *, reason: str, created_at: str):
        wid = workflow.workflow_id
        derived_from_events = len(parents) > 0
        report = self.gate.evaluate(workflow=workflow, parents=tuple(parents),
                                    derived_from_events=derived_from_events, requires_lineage=True)
        self.gate.raise_if_failed(report)
        node = self.lineage.record(make_workflow_lineage(
            wid, parents=parents, workflow_type=workflow.workflow_type, created_at=created_at))
        self.audit.append("workflow_created",
                          {"workflow_id": wid, "workflow_type": workflow.workflow_type,
                           "lineage_id": node.lineage_id, "n_parents": len(parents)},
                          created_at=created_at)
        version = WorkflowVersion.compute(workflow.state_signature(), None)
        workflow = replace(workflow, version=version, lineage_id=node.lineage_id,
                           audit_state=self.audit.head)
        self.audit.append("version_changed", {"workflow_id": wid, "version": version,
                                              "reason": reason}, created_at=created_at)
        workflow = replace(workflow, audit_state=self.audit.head)
        self.registry.register(WorkflowRegistryRecord(
            workflow_id=wid, workflow_type=workflow.workflow_type, subject_id=workflow.subject_id,
            state=workflow.state, version=version, lineage_id=node.lineage_id,
            audit_state=workflow.audit_state, content_signature_value=workflow.state_signature()))
        self.audit.append("workflow_registered", {"workflow_id": wid, "version": version},
                          created_at=created_at)
        workflow = replace(workflow, audit_state=self.audit.head)
        return workflow
