"""Deterministic evidence bundling.

Resolves every evidence reference in a :class:`DecisionContext` to its source
record, summarizes it (preserving the calibrated confidence and abstention from
the V1 signal), and ranks the items deterministically. The bundle includes *all*
evidence in the context — none is suppressed.
"""

from __future__ import annotations

from backend.decision_support.schemas.decision import (
    DecisionContext,
    EvidenceBundle,
    EvidenceSummary,
)
from backend.multi_case_intelligence.population.snapshot import SourcePopulation
from backend.multi_case_intelligence.schemas.source import Evidence


class EvidenceBundler:
    """Builds :class:`EvidenceBundle` artifacts from a context (read-only)."""

    def build_bundle(
        self,
        population: SourcePopulation,
        context: DecisionContext,
        *,
        schema_version: str = "v2.p6.1",
    ) -> EvidenceBundle:
        records: list[Evidence] = []
        for ref in context.evidence_refs:
            rec = population.get(ref)
            if rec is None or not isinstance(rec, Evidence):
                # An unresolved evidence reference is a hard integrity error: the
                # decision layer must never silently drop evidence.
                raise KeyError(f"evidence reference does not resolve: {ref.key}")
            records.append(rec)

        # Deterministic ranking: present (non-abstained) and higher-confidence
        # evidence first, then by id for total stability.
        def sort_key(e: Evidence) -> tuple:
            conf = e.signal.confidence if e.signal is not None else 0.0
            abstained = bool(e.signal.abstained) if e.signal is not None else False
            return (abstained, -conf, e.evidence_id)

        records.sort(key=sort_key)

        items = tuple(
            EvidenceSummary(
                evidence_ref=e.ref(),
                finding_id=e.finding_id,
                modality=e.modality,
                confidence=e.signal.confidence if e.signal is not None else 0.0,
                abstained=bool(e.signal.abstained) if e.signal is not None else False,
                rank=i + 1,
            )
            for i, e in enumerate(records)
        )
        ranking = tuple(e.evidence_id for e in records)
        bundle_id = EvidenceBundle.mint_id(context.id)
        return EvidenceBundle(
            id=bundle_id,
            schema_version=schema_version,
            context_ref=context.ref(),
            items=items,
            ranking=ranking,
        )
