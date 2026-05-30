"""Inference lineage helpers built on the shared ``ml.lineage`` machinery.

No parallel lineage system: a prediction node is recorded in the *same*
``ml.lineage.LineageTracker`` as every upstream node, parenting **both** the model node
and the input feature-asset node. A single ``verify_chain`` from a prediction therefore
reaches the patient:

    Patient -> Case -> EEG -> Processed -> Feature -> Dataset -> Training Run -> Model -> Prediction

(the model path supplies Dataset/Training Run/Model; the input-feature path supplies
the specific Feature -> Processed -> EEG -> Case -> Patient of the recording predicted on).
"""

from __future__ import annotations

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    INFERENCE_FOUNDATION_VERSION, INFERENCE_DOMAIN_VERSION, INFERENCE_IDENTITY_VERSION,
    INFERENCE_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def inference_version_bundle(**extra: object) -> dict:
    bundle = {
        "inference_foundation_version": INFERENCE_FOUNDATION_VERSION,
        "inference_domain_version": INFERENCE_DOMAIN_VERSION,
        "inference_identity_version": INFERENCE_IDENTITY_VERSION,
        "inference_lineage_version": INFERENCE_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_prediction_lineage(prediction_id: str, model_lineage_id: str, feature_lineage_id: str, *,
                            model_id: str, feature_asset_id: str, prediction_fingerprint: str,
                            created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A prediction lineage node parented on the model node + the input feature node."""
    return make_lineage_record(
        kind="prediction", versions=inference_version_bundle(),
        inputs={"model_id": model_id, "feature_asset_id": feature_asset_id},
        outputs={"prediction_id": prediction_id, "prediction_fingerprint": prediction_fingerprint},
        parents=(model_lineage_id, feature_lineage_id), created_at=created_at)
