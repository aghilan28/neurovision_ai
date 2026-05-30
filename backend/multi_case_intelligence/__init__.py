"""Multi-Case Intelligence Layer (V2-P5).

A system capable of understanding *collections* of clinical cases without ever
altering individual case truth. It generates **intelligence** (cohorts,
population analytics, trends, quality analytics) over the populations of
Version 2 cases, reviews, findings, interpretations, knowledge and evidence.

Every intelligence artifact produced here is:

* **Versioned**     — carries a content hash and a monotonic version.
* **Traceable**     — every artifact has a lineage record back to its sources.
* **Auditable**     — every state change is an immutable, hash-chained event.
* **Deterministic** — identical inputs always produce identical outputs
  (no wall-clock, no randomness anywhere in this package).
* **Governed**      — admitted through a governance gate; registered before use.
* **Reproducible**  — any artifact can be regenerated from pinned inputs.

Population intelligence **never modifies source cases** (see
``population.SourcePopulation`` which is immutable).

The public entry point is :class:`~backend.multi_case_intelligence.service.MultiCaseIntelligenceService`.
"""

from backend.multi_case_intelligence.service import MultiCaseIntelligenceService

__all__ = ["MultiCaseIntelligenceService"]

# Logical schema version for the whole subsystem (bump on schema changes).
SUBSYSTEM = "multi_case_intelligence"
SCHEMA_VERSION = "v2.p5.1"
