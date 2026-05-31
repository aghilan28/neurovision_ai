"""``backend/dataset_integration/lineage`` — dataset lineage on the shared tracker (DRP1-I).

No parallel lineage system: dataset nodes are recorded in the same
``ml.lineage.LineageTracker`` as every other node. The chain realized is

    Dataset Source -> Dataset -> Dataset Version (-> Dataset Registry)

so a single ``verify_chain`` from a dataset version reaches its source. Deterministic.
"""

from __future__ import annotations

from ml.lineage import make_lineage_record, LineageTracker, LineageRecord  # allowed: backend -> ml

from ..version import (
    DATASET_INTEGRATION_VERSION, DATASET_DOMAIN_VERSION, DATASET_IDENTITY_VERSION,
    DATASET_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def dataset_version_bundle(**extra) -> dict:
    bundle = {
        "dataset_integration_version": DATASET_INTEGRATION_VERSION,
        "dataset_domain_version": DATASET_DOMAIN_VERSION,
        "dataset_identity_version": DATASET_IDENTITY_VERSION,
        "dataset_lineage_version": DATASET_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_source_lineage(source_id: str, *, source: str,
                        created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="dataset_source", versions=dataset_version_bundle(),
                               inputs={"source": source}, outputs={"source_id": source_id},
                               parents=(), created_at=created_at)


def make_dataset_lineage(dataset_id: str, source_id: str, source_lineage_id: str, *,
                         manifest_fingerprint: str,
                         created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="dataset", versions=dataset_version_bundle(),
        inputs={"source_id": source_id, "manifest_fingerprint": manifest_fingerprint},
        outputs={"dataset_id": dataset_id}, parents=(source_lineage_id,), created_at=created_at)


def make_version_lineage(version_id: str, dataset_id: str, dataset_lineage_id: str, *,
                         version: str, created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="dataset_version", versions=dataset_version_bundle(),
        inputs={"dataset_id": dataset_id, "version": version}, outputs={"version_id": version_id},
        parents=(dataset_lineage_id,), created_at=created_at)


__all__ = ["dataset_version_bundle", "make_source_lineage", "make_dataset_lineage",
           "make_version_lineage", "LineageTracker", "LineageRecord", "make_lineage_record"]
