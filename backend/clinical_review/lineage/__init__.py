"""``backend/clinical_review/lineage`` — review lineage (V2-P2).

Builds content-addressed lineage nodes for reviews + sessions on top of
``ml.lineage``, with parents linking to the Case lineage node and the V1 inference
lineage node, so every review is fully traceable: Review → Session → Case → Study →
Inference → Artifacts.
"""

from __future__ import annotations

from .lineage import (
    review_version_bundle,
    make_review_lineage,
    make_session_lineage,
)
from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

__all__ = ["review_version_bundle", "make_review_lineage", "make_session_lineage",
           "make_lineage_record", "LineageRecord"]
