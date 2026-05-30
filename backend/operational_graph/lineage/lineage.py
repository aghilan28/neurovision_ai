"""Operational-graph lineage helpers built on ml.lineage.

Every graph artifact (node/edge/projection) gets a content-addressed lineage node
whose *parents* are the lineage nodes of the source artifacts it was derived from
(the represented entity/event/timeline/workflow node, or the endpoint nodes for an
edge). A single ``verify_chain`` from a graph artifact therefore spans back to the
patient. Shares the platform's single ``ml.lineage.LineageTracker``.
"""

from __future__ import annotations

from typing import Sequence

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    OPERATIONAL_GRAPH_VERSION, GRAPH_DOMAIN_VERSION, GRAPH_IDENTITY_VERSION,
    GRAPH_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def graph_version_bundle(**extra: object) -> dict:
    bundle = {
        "operational_graph_version": OPERATIONAL_GRAPH_VERSION,
        "graph_domain_version": GRAPH_DOMAIN_VERSION,
        "graph_identity_version": GRAPH_IDENTITY_VERSION,
        "graph_lineage_version": GRAPH_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_graph_lineage(kind: str, artifact_id: str, *, parents: Sequence[str] = (),
                       graph_kind: str = "", created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A graph lineage node parented by the source/endpoint nodes it derives from.

    ``kind`` is the lineage-node kind tag (``graph_node`` | ``graph_edge`` |
    ``graph_projection``); ``graph_kind`` documents the node/edge/projection type.
    """
    return make_lineage_record(
        kind=kind, versions=graph_version_bundle(),
        inputs={"artifact_id": artifact_id, "graph_kind": graph_kind,
                "n_parents": len(tuple(parents))},
        outputs={"artifact_id": artifact_id},
        parents=tuple(p for p in parents if p), created_at=created_at)
