"""``backend/operations_platform/lineage`` — operational lineage (T4-G).

No parallel lineage system: every node is recorded in the same ``ml.lineage.LineageTracker``
as the rest of the platform. The required operational chain is

    Dataset -> Model -> Prediction -> Workflow -> Health Event -> Qualification Event

A health-event node parents the observed Track-3 workflow node (which itself chains back
through Prediction -> Model -> Recording -> Dataset), and a qualification-event node parents
the health-event node — so one ``verify_chain`` from a qualification (or readiness) node
reaches the dataset + model. Deterministic (content-addressed ids; ``created_at`` excluded).
"""

from __future__ import annotations

from ml.lineage import LineageRecord, LineageTracker, make_lineage_record

from ..version import (
    OPERATIONS_PLATFORM_VERSION, OPS_DOMAIN_VERSION, OPS_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def _versions(**extra) -> dict:
    bundle = {"operations_platform_version": OPERATIONS_PLATFORM_VERSION,
              "ops_domain_version": OPS_DOMAIN_VERSION, "ops_lineage_version": OPS_LINEAGE_VERSION}
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_health_lineage(health_check_id, *, parents=(), overall,
                        created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="ops_health_event", versions=_versions(),
                               inputs={"overall": overall},
                               outputs={"health_check_id": health_check_id},
                               parents=tuple(p for p in parents if p), created_at=created_at)


def make_metrics_lineage(metrics_snapshot_id, *, parents=(),
                         created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="ops_metrics_snapshot", versions=_versions(),
                               inputs={"metrics_snapshot_id": metrics_snapshot_id},
                               outputs={"metrics_snapshot_id": metrics_snapshot_id},
                               parents=tuple(p for p in parents if p), created_at=created_at)


def make_diagnostic_lineage(diagnostic_id, *, parents=(),
                            created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="ops_diagnostic", versions=_versions(),
                               inputs={"diagnostic_id": diagnostic_id},
                               outputs={"diagnostic_id": diagnostic_id},
                               parents=tuple(p for p in parents if p), created_at=created_at)


def make_qualification_lineage(qualification_id, health_node, *, status,
                               created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="ops_qualification_event", versions=_versions(),
                               inputs={"status": status},
                               outputs={"qualification_id": qualification_id},
                               parents=tuple(p for p in (health_node,) if p), created_at=created_at)


def make_readiness_lineage(readiness_id, qualification_node, *, classification,
                           created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="ops_readiness", versions=_versions(),
                               inputs={"classification": classification},
                               outputs={"readiness_id": readiness_id},
                               parents=tuple(p for p in (qualification_node,) if p),
                               created_at=created_at)


__all__ = [
    "LineageTracker", "make_health_lineage", "make_metrics_lineage", "make_diagnostic_lineage",
    "make_qualification_lineage", "make_readiness_lineage",
]
