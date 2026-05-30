"""Application lineage helpers built on the shared ``ml.lineage`` machinery.

No parallel lineage system: application nodes are recorded in the *same*
``ml.lineage.LineageTracker`` as every upstream node. The application introduces three
new node kinds — ``user``, ``session``, ``upload`` — plus a ``workflow`` **join node**
that parents both the upload node (the user-supplied recording) and the prediction node
(the reused P1-P5 clinical chain). A single ``verify_chain`` from a workflow node
therefore spans the full required chain:

    User -> Upload -> EEG -> Processed -> Feature -> Model -> Prediction

(the upload branch supplies User/Upload; the prediction branch supplies Model ->
Training Run -> Dataset and Feature -> Processed -> EEG -> Case -> Patient — the P1-P5
chain is never modified, only referenced).
"""

from __future__ import annotations


from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    APPLICATION_BACKEND_VERSION, APPLICATION_DOMAIN_VERSION, APPLICATION_IDENTITY_VERSION,
    APPLICATION_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def application_version_bundle(**extra: object) -> dict:
    bundle = {
        "application_backend_version": APPLICATION_BACKEND_VERSION,
        "application_domain_version": APPLICATION_DOMAIN_VERSION,
        "application_identity_version": APPLICATION_IDENTITY_VERSION,
        "application_lineage_version": APPLICATION_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_user_lineage(user_id: str, *, username: str,
                      created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A root user lineage node (the origin of the user/upload branch)."""
    return make_lineage_record(
        kind="user", versions=application_version_bundle(),
        inputs={"username": username}, outputs={"user_id": user_id},
        parents=(), created_at=created_at)


def make_session_lineage(session_id: str, user_id: str, user_lineage_id: str, *,
                         created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A session lineage node parented on its user node."""
    return make_lineage_record(
        kind="session", versions=application_version_bundle(),
        inputs={"user_id": user_id}, outputs={"session_id": session_id},
        parents=(user_lineage_id,), created_at=created_at)


def make_upload_lineage(upload_id: str, user_id: str, user_lineage_id: str, *,
                        content_fingerprint: str,
                        created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """An upload lineage node parented on its user node (User -> Upload)."""
    return make_lineage_record(
        kind="upload", versions=application_version_bundle(),
        inputs={"user_id": user_id, "content_fingerprint": content_fingerprint},
        outputs={"upload_id": upload_id}, parents=(user_lineage_id,), created_at=created_at)


def make_workflow_lineage(workflow_id: str, upload_lineage_id: str, prediction_lineage_id: str, *,
                          upload_id: str, prediction_id: str,
                          created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """The workflow **join node**: parents the upload node + the prediction node.

    This is what realizes User -> Upload -> ... -> Prediction in a single verifiable
    chain without modifying the P1-P5 lineage."""
    return make_lineage_record(
        kind="workflow", versions=application_version_bundle(),
        inputs={"upload_id": upload_id, "prediction_id": prediction_id},
        outputs={"workflow_id": workflow_id},
        parents=(upload_lineage_id, prediction_lineage_id), created_at=created_at)
