"""Deterministic evidence bundling (V2-P6).

Resolves every evidence item on the context's findings to a summary (preserving
the recorded V1 ``evidence_confidence`` and ``evidence_type``), ranks them
deterministically, and returns an :class:`EvidenceBundle`. The bundle includes
*all* evidence in the context — none is suppressed (no evidence may be hidden).
"""

from __future__ import annotations

from backend.multi_case_intelligence.population import PopulationView

from ..identity import mint_evidence_bundle
from ..models.domain import DecisionContext, EvidenceBundle, EvidenceSummary


class EvidenceBundler:
    """Builds :class:`EvidenceBundle` artifacts from a context (read-only)."""

    def build(self, population: PopulationView, context: DecisionContext) -> EvidenceBundle:
        finding_ids = set(context.finding_ids)
        findings = [f for f in population.findings if f.finding_id in finding_ids]
        items_raw = []
        for f in findings:
            for e in f.evidence:
                items_raw.append((f.finding_id, e))
        if len(items_raw) != len(context.evidence_ids):
            # Defensive: the bundle must surface exactly the context's evidence set.
            ctx_ids = set(context.evidence_ids)
            present = {e.evidence_id for _, e in items_raw}
            missing = ctx_ids - present
            if missing:
                raise KeyError(f"evidence in context does not resolve: {sorted(missing)}")

        # Deterministic ranking: higher recorded confidence first (None last),
        # then by evidence id for total stability.
        def sort_key(pair):
            _, e = pair
            conf = e.evidence_confidence
            return (0 if conf is not None else 1, -(conf or 0.0), e.evidence_id)

        items_raw.sort(key=sort_key)
        items = tuple(
            EvidenceSummary(evidence_id=e.evidence_id, finding_id=fid, evidence_type=e.evidence_type,
                            confidence=e.evidence_confidence, rank=i + 1)
            for i, (fid, e) in enumerate(items_raw))
        ranking = tuple(e.evidence_id for _, e in items_raw)
        ident = mint_evidence_bundle(context.context_id)
        return EvidenceBundle(bundle_id=ident.id, context_id=context.context_id,
                              items=items, ranking=ranking)
