"""``backend/clinical_knowledge/evidence`` — knowledge↔evidence links (V2-P4).

Grounds knowledge artifacts (concepts/terms) in registered evidence (V1 outputs,
findings' evidence), so knowledge is explainable and traceable, never asserted.
"""

from __future__ import annotations

from .evidence import KnowledgeEvidenceManager

__all__ = ["KnowledgeEvidenceManager"]
