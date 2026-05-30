"""Version identities for the Operational Event Foundation (V3-P1).

Every event artifact records the versions that produced it, so an event is
reproducible and auditable for its whole lifetime (AP-5/AP-6/AP-9, NR-10/NR-11).

Events are derived (observed) from the immutable Version 2 audit logs; they never
modify the systems they observe. ``DETERMINISTIC_EPOCH`` is reused so no
wall-clock value ever enters a hashed payload.
"""

from __future__ import annotations

OPERATIONAL_EVENTS_VERSION: str = "operational-events@1.0.0"

EVENT_DOMAIN_VERSION: str = "event-domain@1.0.0"
EVENT_IDENTITY_VERSION: str = "event-identity@1.0.0"
EVENT_TAXONOMY_VERSION: str = "event-taxonomy@1.0.0"
EVENT_LIFECYCLE_VERSION: str = "event-lifecycle@1.0.0"
EVENT_REGISTRY_VERSION: str = "event-registry@1.0.0"
EVENT_RELATIONSHIP_VERSION: str = "event-relationship@1.0.0"
EVENT_AUDIT_VERSION: str = "event-audit@1.0.0"
EVENT_LINEAGE_VERSION: str = "event-lineage@1.0.0"
EVENT_VALIDATION_VERSION: str = "event-validation@1.0.0"
EVENT_REPORT_VERSION: str = "event-report@1.0.0"
EVENT_GENERATION_VERSION: str = "event-generation@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
