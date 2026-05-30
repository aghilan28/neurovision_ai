"""Operational event taxonomy (V3-P1).

A closed, versioned vocabulary of event **categories** and **types**. Every event
must declare a ``(category, type)`` that exists in this taxonomy; the validator
rejects anything else (taxonomy integrity). Governance/quality/validation actions
are first-class categories, so governance actions also become events.

The taxonomy is intentionally a fixed mapping (not open-ended) so that the meaning
of an event is stable and auditable across the platform.
"""

from __future__ import annotations

from ..version import EVENT_TAXONOMY_VERSION


class EventCategory:
    CASE = "case"
    REVIEW = "review"
    FINDING = "finding"
    KNOWLEDGE = "knowledge"
    INTELLIGENCE = "intelligence"
    DECISION = "decision"
    SYSTEM = "system"
    VALIDATION = "validation"
    GOVERNANCE = "governance"
    QUALITY = "quality"


# category -> ordered tuple of permitted event types.
TAXONOMY: dict[str, tuple[str, ...]] = {
    EventCategory.CASE: (
        "CASE_CREATED", "CASE_UPDATED", "CASE_INGESTED", "CASE_PROCESSING",
        "CASE_READY_FOR_REVIEW", "CASE_UNDER_REVIEW", "CASE_REVIEWED",
        "CASE_CLOSED", "CASE_ARCHIVED", "CASE_INFERENCE_ATTACHED",
    ),
    EventCategory.REVIEW: (
        "REVIEW_CREATED", "REVIEW_ASSIGNED", "REVIEW_REASSIGNED", "REVIEW_STARTED",
        "REVIEW_SESSION_ACTIVITY", "REVIEW_SESSION_ENDED", "REVIEW_SUBMITTED",
        "REVIEW_COMPLETED", "REVIEW_REOPENED", "REVIEW_RESUMED", "REVIEW_CLOSED",
        "REVIEW_ARCHIVED",
    ),
    EventCategory.FINDING: (
        "FINDING_CREATED", "FINDING_EVIDENCE_ADDED", "FINDING_INTERPRETED",
        "FINDING_DRAFTED", "FINDING_SUBMITTED", "FINDING_CONFIRMED",
        "FINDING_REVISED", "FINDING_SUPERSEDED", "FINDING_CLOSED", "FINDING_ARCHIVED",
    ),
    EventCategory.KNOWLEDGE: (
        "KNOWLEDGE_SOURCE_ADDED", "KNOWLEDGE_TERM_ADDED", "KNOWLEDGE_CONCEPT_ADDED",
        "KNOWLEDGE_TAXON_ADDED", "KNOWLEDGE_RELATIONSHIP_ADDED",
        "KNOWLEDGE_EVIDENCE_LINKED", "KNOWLEDGE_UPDATED",
    ),
    EventCategory.INTELLIGENCE: (
        "COHORT_BUILT", "ANALYTICS_BUILT", "TREND_BUILT", "QUALITY_BUILT",
        "INTELLIGENCE_SUMMARY_BUILT",
    ),
    EventCategory.DECISION: (
        "DECISION_CONTEXT_BUILT", "EVIDENCE_BUNDLED", "RISK_CONTEXT_BUILT",
        "PRIORITIZATION_BUILT", "GUIDANCE_BUILT", "DECISION_GENERATED",
    ),
    EventCategory.SYSTEM: (
        "SYSTEM_SNAPSHOT_BUILT", "SYSTEM_WORKFLOW_RUN",
    ),
    EventCategory.VALIDATION: (
        "VALIDATION_PASSED", "VALIDATION_FAILED",
    ),
    EventCategory.GOVERNANCE: (
        "GOVERNANCE_GATE_PASSED", "GOVERNANCE_GATE_REJECTED", "ARTIFACT_REGISTERED",
        "VERSION_CHANGED", "EVENT_SUPERSEDED",
    ),
    EventCategory.QUALITY: (
        "QUALITY_VALIDATION_PASSED", "QUALITY_VALIDATION_FAILED",
    ),
}

# Reverse index: type -> category (types are globally unique by construction).
_TYPE_TO_CATEGORY: dict[str, str] = {
    etype: cat for cat, types in TAXONOMY.items() for etype in types
}


class TaxonomyError(ValueError):
    """Raised when a (category, type) pair is not in the taxonomy."""


def categories() -> tuple[str, ...]:
    return tuple(TAXONOMY.keys())


def types_for(category: str) -> tuple[str, ...]:
    if category not in TAXONOMY:
        raise TaxonomyError(f"unknown event category {category!r}")
    return TAXONOMY[category]


def category_of(event_type: str) -> str:
    if event_type not in _TYPE_TO_CATEGORY:
        raise TaxonomyError(f"unknown event type {event_type!r}")
    return _TYPE_TO_CATEGORY[event_type]


def is_valid(category: str, event_type: str) -> bool:
    return category in TAXONOMY and event_type in TAXONOMY[category]


def validate(category: str, event_type: str) -> None:
    if not is_valid(category, event_type):
        raise TaxonomyError(
            f"invalid taxonomy pair: category={category!r} type={event_type!r}")


def to_dict() -> dict:
    return {
        "event_taxonomy_version": EVENT_TAXONOMY_VERSION,
        "n_categories": len(TAXONOMY),
        "n_types": sum(len(v) for v in TAXONOMY.values()),
        "categories": {cat: list(types) for cat, types in TAXONOMY.items()},
    }
