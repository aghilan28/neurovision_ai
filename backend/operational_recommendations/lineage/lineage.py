"""Recommendation-layer lineage helpers built on ml.lineage.

Every recommendation gets a content-addressed lineage node whose *parents* are the
lineage nodes of the upstream artifacts it cites as evidence — the **analytics**
records (and, through them, the **workflows**, **graph** nodes and **events** they
were derived from). Because each analytics node already traces back through
workflow/graph/event/temporal nodes to the patient, a single ``verify_chain`` from
a recommendation spans

    Patient -> ... -> Event -> Workflow -> Graph -> Analytics -> Recommendation

Shares the platform's single ``ml.lineage.LineageTracker`` — no parallel lineage.
"""

from __future__ import annotations

from typing import Sequence

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    OPERATIONAL_RECOMMENDATIONS_VERSION, RECOMMENDATION_DOMAIN_VERSION,
    RECOMMENDATION_IDENTITY_VERSION, RECOMMENDATION_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def recommendation_version_bundle(**extra: object) -> dict:
    bundle = {
        "operational_recommendations_version": OPERATIONAL_RECOMMENDATIONS_VERSION,
        "recommendation_domain_version": RECOMMENDATION_DOMAIN_VERSION,
        "recommendation_identity_version": RECOMMENDATION_IDENTITY_VERSION,
        "recommendation_lineage_version": RECOMMENDATION_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_recommendation_lineage(recommendation_id: str, *, parents: Sequence[str] = (),
                                kind: str = "", scope: str = "",
                                created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A recommendation lineage node parented by the analytics nodes it cites."""
    return make_lineage_record(
        kind="recommendation", versions=recommendation_version_bundle(),
        inputs={"recommendation_id": recommendation_id, "recommendation_kind": kind,
                "scope": scope, "n_parents": len(tuple(parents))},
        outputs={"recommendation_id": recommendation_id},
        parents=tuple(p for p in parents if p), created_at=created_at)
