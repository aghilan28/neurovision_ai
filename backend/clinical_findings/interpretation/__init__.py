"""``backend/clinical_findings/interpretation`` — structured interpretation (V2-P3).

Interpretations are kept **separate** from findings (never merged). This subsystem
builds and evolves immutable ``FindingInterpretation`` values, each referencing
supporting evidence + reviews and carrying a recorded qualitative confidence level.
"""

from __future__ import annotations

from .interpretation import InterpretationManager, VALID_INTERPRETATION_TYPES, InterpretationError

__all__ = ["InterpretationManager", "VALID_INTERPRETATION_TYPES", "InterpretationError"]
