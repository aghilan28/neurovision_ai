"""Feature lineage helpers built on the shared ``ml.lineage`` machinery.

No parallel lineage system: a feature node is recorded in the *same*
``ml.lineage.LineageTracker`` as the Patient/Case/EEG/Processed nodes, parenting the
processed-EEG node. A single ``verify_chain`` from a feature asset therefore reaches:

    Patient -> Case -> EEG Asset -> Processed EEG -> Feature Asset

connecting the feature asset back to the patient with complete traceability.
"""

from __future__ import annotations

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    FEATURE_ENGINEERING_VERSION, FEATURE_DOMAIN_VERSION, FEATURE_IDENTITY_VERSION,
    FEATURE_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def feature_version_bundle(**extra: object) -> dict:
    """The feature-engineering version coordinates embedded in every feature node."""
    bundle = {
        "feature_engineering_version": FEATURE_ENGINEERING_VERSION,
        "feature_domain_version": FEATURE_DOMAIN_VERSION,
        "feature_identity_version": FEATURE_IDENTITY_VERSION,
        "feature_lineage_version": FEATURE_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_feature_lineage(feature_asset_id: str, processed_id: str, processed_lineage_id: str, *,
                         families: tuple[str, ...], n_vectors: int, feature_fingerprint: str,
                         created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A content-addressed feature lineage node, parented on the processed-EEG node."""
    return make_lineage_record(
        kind="feature",
        versions=feature_version_bundle(),
        inputs={"processed_id": processed_id, "feature_asset_id": feature_asset_id},
        outputs={"feature_asset_id": feature_asset_id, "families": list(families),
                 "n_vectors": n_vectors, "feature_fingerprint": feature_fingerprint},
        parents=(processed_lineage_id,),
        created_at=created_at,
    )
