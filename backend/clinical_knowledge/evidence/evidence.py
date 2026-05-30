"""Knowledge evidence links: ground a knowledge artifact in registered evidence."""

from __future__ import annotations

from ..models.domain import KnowledgeEvidenceLink


class KnowledgeEvidenceManager:
    """Builds immutable ``KnowledgeEvidenceLink`` values."""

    @staticmethod
    def link(*, knowledge_id: str, evidence_ref: str, evidence_kind: str) -> KnowledgeEvidenceLink:
        if not knowledge_id or not evidence_ref:
            raise ValueError("knowledge_id and evidence_ref are required")
        return KnowledgeEvidenceLink(knowledge_id=knowledge_id, evidence_ref=evidence_ref,
                                     evidence_kind=evidence_kind)
