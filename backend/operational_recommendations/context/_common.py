"""Shared deterministic helpers for the recommendation engines (V3-P6).

Evidence minting and rounding are centralised so every engine cites evidence the
same way and identical inputs always reproduce identical recommendations.
"""

from __future__ import annotations

from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..models.domain import RecommendationEvidence


def rnd(x: float) -> float:
    r = round(float(x), 6)
    return 0.0 if r == 0 else r


def make_evidence(*, source_kind: str, source_id: str, metric_name: str = "",
                  value: float = 0.0, detail: str = "",
                  lineage_id: Optional[str] = None) -> RecommendationEvidence:
    """Mint a content-addressed evidence reference to a real upstream artifact."""
    eid = "evidence+" + hash_obj({"source_kind": source_kind, "source_id": source_id,
                                  "metric_name": metric_name, "value": value})
    return RecommendationEvidence(evidence_id=eid, source_kind=source_kind, source_id=source_id,
                                  metric_name=metric_name, value=float(value), detail=detail,
                                  lineage_id=lineage_id)


def analytics_evidence(view, category: str, metric_name: str, *, detail: str = ""):
    """Evidence citing a specific analytics metric (resolves the analytics record)."""
    rec = view.first_of_category(category)
    if rec is None:
        return None
    m = rec.metric(metric_name)
    if m is None:
        return None
    return make_evidence(source_kind="analytics", source_id=rec.analytics_id,
                         metric_name=metric_name, value=m.value,
                         detail=detail or m.explanation, lineage_id=rec.lineage_id)
