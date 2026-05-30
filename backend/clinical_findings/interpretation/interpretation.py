"""Structured interpretation management (separate from findings).

Interpretations are immutable values; status/evidence/concept changes return a new
value (via ``replace``). An interpretation is descriptive/contextual only — it is
**not** a diagnosis, recommendation, or decision (those are forbidden / belong to
later phases). Its confidence is a recorded qualitative level, never a probability.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Optional

from ..models.domain import FindingInterpretation
from ..identity import mint_interpretation

VALID_INTERPRETATION_TYPES = ("descriptive", "contextual", "differential-note")
_VALID_STATUS = ("draft", "confirmed", "withdrawn")
_VALID_CONFIDENCE = (None, "low", "moderate", "high")


class InterpretationError(ValueError):
    """Raised on invalid interpretation operations."""


class InterpretationManager:
    """Stateless builders that create/evolve immutable ``FindingInterpretation`` values."""

    @staticmethod
    def new(*, finding_id: str, text: str, interpretation_type: str = "descriptive",
            key: Optional[str] = None, supporting_evidence: Iterable[str] = (),
            confidence_level: Optional[str] = None, review_references: Iterable[str] = (),
            concept_refs: Iterable[str] = ()) -> FindingInterpretation:
        if not text:
            raise InterpretationError("interpretation_text must be non-empty")
        if interpretation_type not in VALID_INTERPRETATION_TYPES:
            raise InterpretationError(f"interpretation_type must be one of {VALID_INTERPRETATION_TYPES}")
        if confidence_level not in _VALID_CONFIDENCE:
            raise InterpretationError(f"confidence_level must be one of {_VALID_CONFIDENCE}")
        key = key or text
        iid = mint_interpretation(finding_id, key).id
        return FindingInterpretation(
            interpretation_id=iid, finding_id=finding_id, interpretation_text=text,
            interpretation_type=interpretation_type, interpretation_status="draft",
            supporting_evidence=tuple(supporting_evidence), confidence_level=confidence_level,
            review_references=tuple(review_references), concept_refs=tuple(concept_refs))

    @staticmethod
    def set_status(interp: FindingInterpretation, status: str) -> FindingInterpretation:
        if status not in _VALID_STATUS:
            raise InterpretationError(f"status must be one of {_VALID_STATUS}")
        return replace(interp, interpretation_status=status)

    @staticmethod
    def attach_concepts(interp: FindingInterpretation, concept_ids: Iterable[str]) -> FindingInterpretation:
        merged = tuple(dict.fromkeys(interp.concept_refs + tuple(concept_ids)))
        return replace(interp, concept_refs=merged)
