"""Serving lineage helpers built on the shared ``ml.lineage`` machinery (DRP3-J).

No parallel lineage system: serving-request / serving-execution / serving-response nodes
are recorded in the *same* ``ml.lineage.LineageTracker`` as every upstream node. The
reused inference foundation already records the ``prediction`` node (parenting the model +
input feature). The serving nodes are wired so a single ``verify_chain`` from a serving
response reaches the patient:

    Dataset -> Feature Asset -> Model -> Inference (prediction) -> Serving Request ->
    Serving Execution -> Serving Response

The request node parents the model + input-feature nodes (its declared inputs); the
execution node parents the request node + the prediction node (tying the request to the
produced inference); the response node parents the execution node — so the serving response
verify_chains all the way back to the patient.
"""

from __future__ import annotations

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    SERVING_PLATFORM_VERSION, SERVING_DOMAIN_VERSION, SERVING_IDENTITY_VERSION,
    SERVING_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)

__all__ = [
    "make_serving_request_lineage", "make_serving_execution_lineage",
    "make_serving_response_lineage", "serving_version_bundle",
]


def serving_version_bundle(**extra: object) -> dict:
    bundle = {
        "serving_platform_version": SERVING_PLATFORM_VERSION,
        "serving_domain_version": SERVING_DOMAIN_VERSION,
        "serving_identity_version": SERVING_IDENTITY_VERSION,
        "serving_lineage_version": SERVING_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_serving_request_lineage(request_id: str, model_lineage_id: str, feature_lineage_id: str, *,
                                 model_id: str, feature_asset_id: str,
                                 created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A serving-request node parented on the model node + the input feature node."""
    return make_lineage_record(
        kind="serving_request", versions=serving_version_bundle(),
        inputs={"model_id": model_id, "feature_asset_id": feature_asset_id},
        outputs={"request_id": request_id}, parents=(model_lineage_id, feature_lineage_id),
        created_at=created_at)


def make_serving_execution_lineage(execution_id: str, request_lineage_id: str,
                                   prediction_lineage_id: str, *, prediction_id: str,
                                   created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A serving-execution node parented on the request node + the inference prediction node."""
    return make_lineage_record(
        kind="serving_execution", versions=serving_version_bundle(),
        inputs={"request_id": request_lineage_id, "prediction_id": prediction_id},
        outputs={"execution_id": execution_id}, parents=(request_lineage_id, prediction_lineage_id),
        created_at=created_at)


def make_serving_response_lineage(response_id: str, execution_lineage_id: str, *,
                                  predicted_class: int,
                                  created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A serving-response node parented on the execution node."""
    return make_lineage_record(
        kind="serving_response", versions=serving_version_bundle(),
        inputs={"execution_id": execution_lineage_id},
        outputs={"response_id": response_id, "predicted_class": predicted_class},
        parents=(execution_lineage_id,), created_at=created_at)
