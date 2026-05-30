"""OperationalEventService — the governed orchestration hub for V3-P1.

Records operational **events** (facts about meaningful changes) and their
relationships, without ever modifying the systems it observes. Every event is
produced through one governed path: governance gate (architecture/quality/context/
risk) → shared-lineage node parented by the observed source-entity node →
immutable audit event → content-addressed version → registry sync.

It shares the platform's single ``ml.lineage.LineageTracker`` so a single
``verify_chain`` from an event spans back to the patient root. Events observe; they
do not own. Supersession records a new event + a governed status flip on the old
one — it never rewrites a fact.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional, Sequence

from ml.lineage import LineageTracker  # allowed: backend -> ml

from .version import DETERMINISTIC_EPOCH
from .identity import LogicalClock, mint_event, mint_relationship
from .taxonomy import category_of, validate as taxonomy_validate
from .models.domain import (
    EventRecord, EventMetadata, EventRelationship, EventVersion, EventRegistryRecord,
)
from .audit import make_event_audit_log
from .lineage import make_event_lineage
from .registry import EventRegistry
from .lifecycle import check_transition, SUPERSEDED
from .validation import EventGovernanceGate, EventValidator
from .reports import (
    build_event_summary_report, build_event_taxonomy_report, build_event_registry_report,
    build_relationship_report, build_event_validation_report, build_event_audit_report,
    build_event_lineage_report,
)


class OperationalEventService:
    """Stateful service: event registry, shared lineage tracker, immutable audit log."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[EventRegistry] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or EventRegistry()
        self.audit = make_event_audit_log()
        self.gate = EventGovernanceGate()
        self.validator = EventValidator()

    # --- recording ------------------------------------------------------------
    def record_event(self, *, event_type: str, source_entity_id: str, source_version: str,
                     source_audit_event_hash: str, clock: LogicalClock,
                     source_kind: str, actor: str = "system", summary: str = "",
                     payload: Optional[dict] = None, parents: Sequence[str] = (),
                     supersedes: Optional[str] = None,
                     created_at: str = DETERMINISTIC_EPOCH) -> EventRecord:
        """Mint, govern, lineage, audit, version and register one event."""
        category = category_of(event_type)            # raises TaxonomyError if unknown
        taxonomy_validate(category, event_type)
        ident = mint_event(event_type=event_type, category=category,
                            source_entity_id=source_entity_id, source_version=source_version,
                            clock=clock)
        metadata = EventMetadata(source_kind=source_kind,
                                 source_audit_event_hash=source_audit_event_hash,
                                 actor=actor, summary=summary)
        event = EventRecord(event_id=ident.id, event_type=event_type, category=category,
                            source_entity_id=source_entity_id, source_version=source_version,
                            clock=clock, metadata=metadata, payload=dict(payload or {}),
                            supersedes=supersedes)

        # 1. governance gate
        gate_parents = tuple(parents)
        report = self.gate.evaluate(event=event, parents=gate_parents, requires_lineage=True)
        self.gate.raise_if_failed(report)

        # 2. lineage node parented by the observed source entity node(s)
        node = self.lineage.record(make_event_lineage(
            ident.id, parents=gate_parents, source_kind=source_kind, created_at=created_at))

        # 3. immutable audit: creation
        self.audit.append("event_created",
                          {"event_id": ident.id, "event_type": event_type, "category": category,
                           "source_entity_id": source_entity_id, "lineage_id": node.lineage_id,
                           "source_audit_event_hash": source_audit_event_hash},
                          created_at=created_at)

        # 4. content-addressed version (chains from the superseded event, if any)
        version = EventVersion.compute(event.state_signature(), supersedes)
        event = replace(event, version=version, lineage_id=node.lineage_id,
                        audit_state=self.audit.head)
        self.audit.append("version_changed",
                          {"event_id": ident.id, "version": version, "reason": "event_recorded"},
                          created_at=created_at)
        event = replace(event, audit_state=self.audit.head)

        # 5. registry sync
        self.registry.register(EventRegistryRecord(
            event_id=ident.id, event_type=event_type, category=category,
            source_entity_id=source_entity_id, version=version, lineage_id=node.lineage_id,
            audit_state=event.audit_state, status=event.status,
            content_signature_value=event.state_signature()))
        self.audit.append("event_registered", {"event_id": ident.id, "version": version},
                          created_at=created_at)
        event = replace(event, audit_state=self.audit.head)

        # 6. supersession: record the relationship + flip the old event's status
        if supersedes is not None:
            self.relate(ident.id, supersedes, target_kind="event", relation="supersedes",
                        created_at=created_at)
            if self.registry.exists(supersedes):
                old = self.registry.get(supersedes)
                check_transition(old.status, SUPERSEDED)
                self.registry.mark_superseded(supersedes)
                self.audit.append("event_superseded",
                                  {"superseded_event_id": supersedes, "by_event_id": ident.id},
                                  created_at=created_at)
        # The event's own observation edge to its source entity.
        return event

    def observe(self, source_entity_id: str, *, target_kind: str,
                created_at: str = DETERMINISTIC_EPOCH) -> None:  # pragma: no cover - convenience
        """(reserved) explicit observation edge; observation is implied by lineage."""

    # --- relationships --------------------------------------------------------
    def relate(self, source_event_id: str, target_id: str, *, target_kind: str,
               relation: str, created_at: str = DETERMINISTIC_EPOCH) -> EventRelationship:
        """Create an immutable relationship edge from an event to another entity/event."""
        rid = mint_relationship(source_event_id=source_event_id, target_id=target_id,
                                relation=relation)
        rel = EventRelationship(relationship_id=rid, source_event_id=source_event_id,
                                target_id=target_id, target_kind=target_kind, relation=relation)
        self.registry.register_relationship(rel)
        self.audit.append("relationship_created",
                          {"relationship_id": rid, "source_event_id": source_event_id,
                           "target_id": target_id, "relation": relation}, created_at=created_at)
        return rel

    def link_sequence(self, ordered_event_ids: Sequence[str],
                      created_at: str = DETERMINISTIC_EPOCH) -> list[EventRelationship]:
        """Create sequence edges e0→e1→e2… (operational ordering chain)."""
        out = []
        ids = list(ordered_event_ids)
        for prev, nxt in zip(ids, ids[1:]):
            out.append(self.relate(prev, nxt, target_kind="event", relation="sequence",
                                   created_at=created_at))
        return out

    # --- validation -----------------------------------------------------------
    def validate(self, event: EventRecord):
        return self.validator.validate(event=event, registry=self.registry,
                                       audit_log=self.audit, lineage_tracker=self.lineage)

    # --- reports --------------------------------------------------------------
    def reports(self) -> dict:
        return {
            "event_summary_report": build_event_summary_report(self.registry),
            "event_taxonomy_report": build_event_taxonomy_report(),
            "event_registry_report": build_event_registry_report(self.registry),
            "relationship_report": build_relationship_report(self.registry),
            "event_audit_report": build_event_audit_report(self.audit),
        }

    def lineage_report(self, event: EventRecord) -> dict:
        return build_event_lineage_report(event, self.lineage)

    def validation_report(self, scope: str, validation_report_dict: dict) -> dict:
        return build_event_validation_report(scope, validation_report_dict)
