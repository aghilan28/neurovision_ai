"""``backend/operational_events`` — Operational Event Foundation (V3-P1).

Introduces **events** as first-class platform entities. Version 2 stored *state*;
Version 3 stores *facts about change*. An event records a meaningful change that
occurred within the system and becomes a permanent operational record.

Every event is **immutable, versioned, traceable, auditable, lineage-tracked,
recoverable, and governed**. Events are facts: they are **never edited**; they may
be **superseded** (a new event references the one it supersedes), never rewritten.

Events are **derived (observed)** from the immutable Version 2 audit logs via the
generation framework's adapters — *events observe systems; events do not own
systems*. Nothing in Version 0/1/2 is modified. The subsystem shares the platform's
single ``ml.lineage.LineageTracker`` (no parallel lineage), the shared
``ImmutableAuditLog`` (no replacement audit system), and a dedicated event registry
(no parallel registry for existing entities).

Determinism (NR-9/NR-10): there is no wall-clock anywhere. "Time" is a deterministic
:class:`LogicalClock` — ``(ingestion_ordinal, source_seq, epoch)`` — so identical
source facts always mint identical event ids and versions.

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` and the
sibling V2 subsystems it observes; never imports ``frontend``. Scope is strictly
V3-P1 — no knowledge graph, no operational analytics/recommendations/dashboards, no
FHIR/HL7/EMR, no realtime streaming, no V4. See ``.gcc/decisions/ADR-0007``.
"""

from __future__ import annotations

from .version import (
    OPERATIONAL_EVENTS_VERSION, EVENT_DOMAIN_VERSION, EVENT_IDENTITY_VERSION,
    EVENT_TAXONOMY_VERSION, EVENT_LIFECYCLE_VERSION, EVENT_REGISTRY_VERSION,
    EVENT_RELATIONSHIP_VERSION, EVENT_AUDIT_VERSION, EVENT_LINEAGE_VERSION,
    EVENT_VALIDATION_VERSION, EVENT_REPORT_VERSION, EVENT_GENERATION_VERSION,
)
from .identity import (
    LogicalClock, EventIdentity, EventIdentityError, mint_event, mint_relationship,
    validate_identity, validate_relationship_identity,
)
from . import taxonomy
from .taxonomy import EventCategory, TaxonomyError
from . import lifecycle
from .lifecycle import EventLifecycleError
from .models import (
    EventMetadata, EventRecord, EventRelationship, EventAuditRecord, EventVersion,
    EventLineageRecord, EventRegistryRecord,
)
from .audit import make_event_audit_log
from .registry import EventRegistry
from .validation import EventGovernanceGate, EventValidator, EventValidationError
from .generation import (
    CaseEventAdapter, ReviewEventAdapter, FindingEventAdapter, KnowledgeEventAdapter,
    IntelligenceEventAdapter, DecisionEventAdapter, ADAPTERS,
)
from .service import OperationalEventService

__all__ = [
    "OPERATIONAL_EVENTS_VERSION", "EVENT_DOMAIN_VERSION", "EVENT_IDENTITY_VERSION",
    "EVENT_TAXONOMY_VERSION", "EVENT_LIFECYCLE_VERSION", "EVENT_REGISTRY_VERSION",
    "EVENT_RELATIONSHIP_VERSION", "EVENT_AUDIT_VERSION", "EVENT_LINEAGE_VERSION",
    "EVENT_VALIDATION_VERSION", "EVENT_REPORT_VERSION", "EVENT_GENERATION_VERSION",
    "LogicalClock", "EventIdentity", "EventIdentityError", "mint_event", "mint_relationship",
    "validate_identity", "validate_relationship_identity",
    "taxonomy", "EventCategory", "TaxonomyError", "lifecycle", "EventLifecycleError",
    "EventMetadata", "EventRecord", "EventRelationship", "EventAuditRecord", "EventVersion",
    "EventLineageRecord", "EventRegistryRecord",
    "make_event_audit_log", "EventRegistry",
    "EventGovernanceGate", "EventValidator", "EventValidationError",
    "CaseEventAdapter", "ReviewEventAdapter", "FindingEventAdapter", "KnowledgeEventAdapter",
    "IntelligenceEventAdapter", "DecisionEventAdapter", "ADAPTERS",
    "OperationalEventService",
]
