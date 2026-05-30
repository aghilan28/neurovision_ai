"""TemporalIntelligenceService — the governed orchestration hub for V3-P2.

Derives temporal artifacts (timelines, histories, evolution records, temporal
analytics) **from events** (V3-P1) and admits each through one governed path:
governance gate (architecture/quality/context/risk) → shared-lineage node parented
by the **event** lineage nodes it derives from → immutable audit event →
content-addressed version → registry sync.

Because each artifact's lineage parents are event nodes (which already trace to the
patient), a single ``verify_chain`` spans Patient → ... → Event → Temporal artifact.
No hidden state reconstruction: everything is read from the recorded events via the
:class:`EventSourceView`. It shares the platform's single ``ml.lineage.LineageTracker``.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional, Sequence

from ml.lineage import LineageTracker  # allowed: backend -> ml

from .version import DETERMINISTIC_EPOCH
from .timelines import EventSourceView, TimelineEngine
from .history import HistoryEngine
from .evolution import EvolutionEngine
from .analytics import TemporalAnalyticsEngine
from .models.domain import (
    TemporalVersion, TemporalRegistryRecord, artifact_id_of, artifact_kind_of,
)
from .audit import make_temporal_audit_log
from .lineage import make_temporal_lineage
from .registry import TemporalRegistry
from .validation import TemporalGovernanceGate, TemporalValidator
from .schemas import all_contracts
from .reports import (
    build_timeline_report, build_history_report, build_evolution_report,
    build_temporal_analytics_report, build_validation_report, build_audit_report,
    build_lineage_report,
)


class TemporalIntelligenceService:
    """Stateful service: temporal registry, shared lineage tracker, immutable audit log."""

    def __init__(self, event_service, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[TemporalRegistry] = None):
        # event_service: backend.operational_events.OperationalEventService
        self.events = event_service
        self.lineage = lineage_tracker or event_service.lineage
        self.registry = registry or TemporalRegistry()
        self.audit = make_temporal_audit_log()
        self.gate = TemporalGovernanceGate()
        self.validator = TemporalValidator()
        self._timeline = TimelineEngine()
        self._history = HistoryEngine()
        self._evolution = EvolutionEngine()
        self._analytics = TemporalAnalyticsEngine()
        self._view: Optional[EventSourceView] = None

    # --- event source view ----------------------------------------------------
    def view(self) -> EventSourceView:
        """Build (once) the deterministic event-source view from full event records.

        Reconstructs EventRecord-like objects from the registry is not needed: the
        service expects the event objects to be supplied via :meth:`load_events`.
        """
        if self._view is None:
            raise RuntimeError("call load_events(...) before deriving temporal artifacts")
        return self._view

    def load_events(self, events: Sequence) -> "TemporalIntelligenceService":
        """Provide the recorded EventRecord objects to derive temporal artifacts from."""
        self._view = EventSourceView(events)
        return self

    # --- event lineage parents ------------------------------------------------
    def _event_parents(self, events: Sequence) -> tuple:
        return tuple(e.lineage_id for e in events if getattr(e, "lineage_id", None))

    # --- builders -------------------------------------------------------------
    def build_timeline(self, *, subject_kind: str, subject_id: str,
                       source_entity_ids: Sequence[str],
                       created_at: str = DETERMINISTIC_EPOCH):
        view = self.view()
        artifact = self._timeline.build(view, subject_kind=subject_kind, subject_id=subject_id,
                                        source_entity_ids=source_entity_ids)
        parents = self._event_parents(view.for_sources(source_entity_ids))
        return self._finalize(artifact, parents, reason="timeline_built", created_at=created_at)

    def build_operational_timeline(self, created_at: str = DETERMINISTIC_EPOCH):
        view = self.view()
        artifact = self._timeline.build_operational(view)
        return self._finalize(artifact, self._event_parents(view.all()),
                              reason="operational_timeline_built", created_at=created_at)

    def build_history(self, *, subject_kind: str, subject_id: str,
                      source_entity_ids: Sequence[str], created_at: str = DETERMINISTIC_EPOCH):
        view = self.view()
        artifact = self._history.build(view, subject_kind=subject_kind, subject_id=subject_id,
                                       source_entity_ids=source_entity_ids)
        parents = self._event_parents(view.for_sources(source_entity_ids))
        return self._finalize(artifact, parents, reason="history_built", created_at=created_at)

    def build_evolution(self, *, subject_kind: str, subject_id: str,
                        source_entity_ids: Sequence[str], created_at: str = DETERMINISTIC_EPOCH):
        view = self.view()
        artifact = self._evolution.build(view, subject_kind=subject_kind, subject_id=subject_id,
                                         source_entity_ids=source_entity_ids)
        parents = self._event_parents(view.for_sources(source_entity_ids))
        return self._finalize(artifact, parents, reason="evolution_built", created_at=created_at)

    def build_analytics(self, *, scope: str = "operational",
                        created_at: str = DETERMINISTIC_EPOCH):
        view = self.view()
        artifact = self._analytics.build(view, scope=scope)
        return self._finalize(artifact, self._event_parents(view.all()),
                              reason="temporal_analytics_built", created_at=created_at)

    # --- validation + reports + viz ------------------------------------------
    def validate(self, artifact, kind: str):
        return self.validator.validate(artifact=artifact, kind=kind, registry=self.registry,
                                       audit_log=self.audit, lineage_tracker=self.lineage)

    def visualization_contracts(self, *, timeline, evolution, analytics) -> list:
        return all_contracts(timeline=timeline, evolution=evolution, analytics=analytics)

    def reports(self, *, timeline=None, history=None, evolution=None, analytics=None) -> dict:
        out: dict = {"audit_report": build_audit_report(self.audit)}
        if timeline is not None:
            out["timeline_report"] = build_timeline_report(timeline)
        if history is not None:
            out["history_report"] = build_history_report(history)
        if evolution is not None:
            out["evolution_report"] = build_evolution_report(evolution)
        if analytics is not None:
            out["temporal_analytics_report"] = build_temporal_analytics_report(analytics)
        return out

    def validation_report(self, scope: str, validation_report_dict: dict) -> dict:
        return build_validation_report(scope, validation_report_dict)

    def lineage_report(self, artifact) -> dict:
        return build_lineage_report(artifact, self.lineage)

    # --- internals ------------------------------------------------------------
    def _finalize(self, artifact, parents: tuple, *, reason: str, created_at: str):
        aid = artifact_id_of(artifact)
        kind = artifact_kind_of(artifact)
        derived_from_events = len(parents) > 0
        report = self.gate.evaluate(artifact=artifact, kind=kind, parents=tuple(parents),
                                    derived_from_events=derived_from_events, requires_lineage=True)
        self.gate.raise_if_failed(report)
        node = self.lineage.record(make_temporal_lineage(kind, aid, parents=parents,
                                                        scope=getattr(artifact, "scope", ""),
                                                        created_at=created_at))
        self.audit.append(f"{kind}_created",
                          {"artifact_id": aid, "lineage_id": node.lineage_id,
                           "n_event_parents": len(parents)}, created_at=created_at)
        version = TemporalVersion.compute(artifact.state_signature(), None)
        artifact = replace(artifact, version=version, lineage_id=node.lineage_id,
                           audit_state=self.audit.head)
        self.audit.append("version_changed", {"artifact_id": aid, "version": version,
                                              "reason": reason}, created_at=created_at)
        artifact = replace(artifact, audit_state=self.audit.head)
        self.registry.register(TemporalRegistryRecord(
            artifact_id=aid, artifact_kind=kind, scope=getattr(artifact, "scope", ""),
            version=version, lineage_id=node.lineage_id, audit_state=artifact.audit_state,
            content_signature_value=artifact.state_signature()))
        self.audit.append(f"{kind}_registered", {"artifact_id": aid, "version": version},
                          created_at=created_at)
        artifact = replace(artifact, audit_state=self.audit.head)
        return artifact
