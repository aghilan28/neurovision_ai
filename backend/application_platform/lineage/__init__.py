"""``backend/application_platform/lineage`` — product workflow lineage (T3-J).

No parallel lineage system: every node is recorded in the same ``ml.lineage.LineageTracker``
as the rest of the platform. The required chain is

    Dataset -> Recording -> Model -> Prediction Request -> Prediction Result -> Report

The prediction-request node parents both the **upload** node (the real recording) and the
**model** node (the Track-2 candidate), so one ``verify_chain`` from a report reaches the
recording, the model, and — through the reused ``application_backend`` workflow lineage —
the patient. Deterministic (content-addressed ids; ``created_at`` excluded from the id).
"""

from __future__ import annotations

from ml.lineage import LineageRecord, LineageTracker, make_lineage_record

from ..version import (
    APP_LINEAGE_VERSION, APPLICATION_PLATFORM_VERSION, APP_DOMAIN_VERSION, DETERMINISTIC_EPOCH,
)


def _versions(**extra) -> dict:
    bundle = {"application_platform_version": APPLICATION_PLATFORM_VERSION,
              "app_domain_version": APP_DOMAIN_VERSION, "app_lineage_version": APP_LINEAGE_VERSION}
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_upload_lineage(upload_id, *, parents=(), content_fingerprint,
                        created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="app_upload", versions=_versions(),
                               inputs={"content_fingerprint": content_fingerprint},
                               outputs={"upload_id": upload_id}, parents=tuple(parents),
                               created_at=created_at)


def make_model_ref_lineage(model_id, *, parents=(), architecture,
                           created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="app_model_ref", versions=_versions(),
                               inputs={"architecture": architecture},
                               outputs={"model_id": model_id}, parents=tuple(parents),
                               created_at=created_at)


def make_prediction_request_lineage(prediction_request_id, upload_node, model_node, *,
                                    created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    parents = tuple(n for n in (upload_node, model_node) if n)
    return make_lineage_record(kind="app_prediction_request", versions=_versions(),
                               inputs={"upload_node": upload_node, "model_node": model_node},
                               outputs={"prediction_request_id": prediction_request_id},
                               parents=parents, created_at=created_at)


def make_prediction_result_lineage(prediction_result_id, request_node, *,
                                   created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="app_prediction_result", versions=_versions(),
                               inputs={"request_node": request_node},
                               outputs={"prediction_result_id": prediction_result_id},
                               parents=(request_node,), created_at=created_at)


def make_report_lineage(report_id, result_node, *, created_at=DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(kind="app_report", versions=_versions(),
                               inputs={"result_node": result_node},
                               outputs={"report_id": report_id}, parents=(result_node,),
                               created_at=created_at)


__all__ = [
    "LineageTracker", "make_upload_lineage", "make_model_ref_lineage",
    "make_prediction_request_lineage", "make_prediction_result_lineage", "make_report_lineage",
]
