"""Analytics-layer lineage helpers built on ml.lineage.

Every analytics record gets a content-addressed lineage node whose *parents* are
the lineage nodes of the upstream artifacts it derives from — the **events**,
**workflows**, **graph** nodes and **temporal analytics** it summarizes. Because
each of those nodes already traces back to its source entity and the patient, a
single ``verify_chain`` from an analytics record spans

    Patient -> ... -> Event -> (Timeline) -> Workflow -> Graph -> Analytics

Shares the platform's single ``ml.lineage.LineageTracker`` — no parallel lineage.
"""

from __future__ import annotations

from typing import Sequence

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    OPERATIONAL_ANALYTICS_VERSION, ANALYTICS_DOMAIN_VERSION, ANALYTICS_IDENTITY_VERSION,
    ANALYTICS_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def analytics_version_bundle(**extra: object) -> dict:
    bundle = {
        "operational_analytics_version": OPERATIONAL_ANALYTICS_VERSION,
        "analytics_domain_version": ANALYTICS_DOMAIN_VERSION,
        "analytics_identity_version": ANALYTICS_IDENTITY_VERSION,
        "analytics_lineage_version": ANALYTICS_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_analytics_lineage(analytics_id: str, *, parents: Sequence[str] = (),
                           category: str = "", scope: str = "",
                           created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """An analytics lineage node parented by the upstream nodes it derives from."""
    return make_lineage_record(
        kind="analytics", versions=analytics_version_bundle(),
        inputs={"analytics_id": analytics_id, "category": category, "scope": scope,
                "n_parents": len(tuple(parents))},
        outputs={"analytics_id": analytics_id},
        parents=tuple(p for p in parents if p), created_at=created_at)
