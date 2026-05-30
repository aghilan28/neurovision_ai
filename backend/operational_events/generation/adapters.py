"""Event generation framework — adapters that observe V2 systems (V3-P1).

These adapters **observe** the immutable audit logs and registries of the Version
2 subsystems and emit operational events. They do not modify, wrap, or own those
systems (events observe systems; events do not own systems). Each adapter:

  * reads a subsystem's audit log entries (already immutable, already hash-chained),
  * maps each audit ``kind`` to a taxonomy event type,
  * derives a deterministic :class:`LogicalClock` from (ingestion ordinal, source
    audit ``seq``, source ``created_at``),
  * records an event whose lineage parent is the source entity's lineage node, so
    the event traces back to the patient.

The mapping is data-only; if a source audit kind has no mapping, the adapter skips
it (a missing mapping is never an invented event).
"""

from __future__ import annotations

from typing import Optional

from ..identity import LogicalClock
from ..service import OperationalEventService


# --- audit-kind -> event-type maps (per source subsystem) --------------------
CASE_MAP = {
    "case_created": "CASE_CREATED",
    "case_inference_attached": "CASE_INFERENCE_ATTACHED",
    "transition:ingested": "CASE_INGESTED",
    "transition:processing": "CASE_PROCESSING",
    "transition:ready_for_review": "CASE_READY_FOR_REVIEW",
    "transition:under_review": "CASE_UNDER_REVIEW",
    "transition:reviewed": "CASE_REVIEWED",
    "transition:closed": "CASE_CLOSED",
    "transition:archived": "CASE_ARCHIVED",
}
REVIEW_MAP = {
    "review_created": "REVIEW_CREATED",
    "assignment_created": "REVIEW_ASSIGNED",
    "assignment_reassigned": "REVIEW_REASSIGNED",
    "session_started": "REVIEW_STARTED",
    "session_activity": "REVIEW_SESSION_ACTIVITY",
    "session_ended": "REVIEW_SESSION_ENDED",
    "transition:pending_confirmation": "REVIEW_SUBMITTED",
    "transition:completed": "REVIEW_COMPLETED",
    "transition:reopened": "REVIEW_REOPENED",
    "transition:closed": "REVIEW_CLOSED",
    "transition:archived": "REVIEW_ARCHIVED",
}
FINDING_MAP = {
    "finding_created": "FINDING_CREATED",
    "evidence_added": "FINDING_EVIDENCE_ADDED",
    "interpretation_added": "FINDING_INTERPRETED",
    "transition:draft": "FINDING_DRAFTED",
    "transition:under_review": "FINDING_SUBMITTED",
    "transition:confirmed": "FINDING_CONFIRMED",
    "transition:revised": "FINDING_REVISED",
    "transition:superseded": "FINDING_SUPERSEDED",
    "transition:closed": "FINDING_CLOSED",
    "transition:archived": "FINDING_ARCHIVED",
}
KNOWLEDGE_MAP = {
    "knowledge_source": "KNOWLEDGE_SOURCE_ADDED",
    "term_added": "KNOWLEDGE_TERM_ADDED",
    "concept_added": "KNOWLEDGE_CONCEPT_ADDED",
    "taxon_added": "KNOWLEDGE_TAXON_ADDED",
    "relationship_added": "KNOWLEDGE_RELATIONSHIP_ADDED",
    "evidence_linked": "KNOWLEDGE_EVIDENCE_LINKED",
}
INTELLIGENCE_MAP = {
    "cohort_created": "COHORT_BUILT",
    "analytics_created": "ANALYTICS_BUILT",
    "trend_created": "TREND_BUILT",
    "quality_created": "QUALITY_BUILT",
    "intel_report_created": "INTELLIGENCE_SUMMARY_BUILT",
}
DECISION_MAP = {
    "decision_context_created": "DECISION_CONTEXT_BUILT",
    "evidence_bundle_created": "EVIDENCE_BUNDLED",
    "risk_context_created": "RISK_CONTEXT_BUILT",
    "prioritization_created": "PRIORITIZATION_BUILT",
    "guidance_created": "GUIDANCE_BUILT",
    "decision_support_created": "DECISION_GENERATED",
}


def _normalize_kind(kind: str, payload: dict) -> str:
    """Normalize a source audit kind for mapping.

    Lifecycle transitions are audited as ``state_change``/``status_change`` with the
    destination in ``to_state``; we key them as ``transition:<to_state>`` so the
    per-subsystem maps can name each lifecycle target explicitly.
    """
    if kind in ("state_change", "status_change", "transition", "lifecycle"):
        target = (payload.get("to_state") or payload.get("to") or payload.get("target")
                  or payload.get("status"))
        if target:
            return f"transition:{target}"
    return kind


class _BaseAdapter:
    """Observe one source audit log and emit events for the mapped kinds."""

    source_kind = "system"
    kind_map: dict = {}

    def __init__(self, service: OperationalEventService) -> None:
        self.service = service

    def observe_log(self, *, source_entity_id: str, source_version: str, audit_log,
                    source_lineage_id: Optional[str], ingestion_ordinal: int,
                    created_at: str) -> list:
        """Emit one event per mapped audit entry in the source log (in order)."""
        emitted = []
        parents = (source_lineage_id,) if source_lineage_id else ()
        for ev in audit_log.events():
            mapped_key = _normalize_kind(ev.kind, ev.payload)
            event_type = self.kind_map.get(mapped_key)
            if event_type is None:
                continue
            clock = LogicalClock(ingestion_ordinal=ingestion_ordinal, source_seq=ev.seq,
                                 epoch=ev.created_at)
            event = self.service.record_event(
                event_type=event_type, source_entity_id=source_entity_id,
                source_version=source_version, source_audit_event_hash=ev.event_hash,
                clock=clock, source_kind=self.source_kind, actor="system",
                summary=f"{self.source_kind} {event_type}", payload={"source_kind": ev.kind},
                parents=parents, created_at=created_at)
            emitted.append(event)
        return emitted


class CaseEventAdapter(_BaseAdapter):
    source_kind = "case"
    kind_map = CASE_MAP


class ReviewEventAdapter(_BaseAdapter):
    source_kind = "review"
    kind_map = REVIEW_MAP


class FindingEventAdapter(_BaseAdapter):
    source_kind = "finding"
    kind_map = FINDING_MAP


class KnowledgeEventAdapter(_BaseAdapter):
    source_kind = "knowledge"
    kind_map = KNOWLEDGE_MAP


class IntelligenceEventAdapter(_BaseAdapter):
    source_kind = "intelligence"
    kind_map = INTELLIGENCE_MAP


class DecisionEventAdapter(_BaseAdapter):
    source_kind = "decision"
    kind_map = DECISION_MAP


ADAPTERS = {
    "case": CaseEventAdapter, "review": ReviewEventAdapter, "finding": FindingEventAdapter,
    "knowledge": KnowledgeEventAdapter, "intelligence": IntelligenceEventAdapter,
    "decision": DecisionEventAdapter,
}
