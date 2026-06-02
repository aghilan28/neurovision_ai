"""Clinical-review lineage helpers built on ml.lineage."""

from __future__ import annotations

from typing import Optional

from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

from ..version import (
    CLINICAL_REVIEW_VERSION, REVIEW_DOMAIN_VERSION, REVIEW_IDENTITY_VERSION,
    REVIEW_LINEAGE_VERSION, DETERMINISTIC_EPOCH,
)


def review_version_bundle(**extra: object) -> dict:
    bundle = {
        "clinical_review_version": CLINICAL_REVIEW_VERSION,
        "review_domain_version": REVIEW_DOMAIN_VERSION,
        "review_identity_version": REVIEW_IDENTITY_VERSION,
        "review_lineage_version": REVIEW_LINEAGE_VERSION,
    }
    bundle.update({k: v for k, v in extra.items() if v is not None})
    return bundle


def make_review_lineage(review_id: str, case_id: str, *, case_lineage_id: str,
                        inference_lineage_id: Optional[str] = None,
                        created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    """A review lineage node; parents = case node (+ inference node if linked)."""
    parents = [case_lineage_id]
    if inference_lineage_id:
        parents.append(inference_lineage_id)
    return make_lineage_record(
        kind="review", versions=review_version_bundle(),
        inputs={"case_id": case_id, "review_id": review_id,
                "inference_lineage_id": inference_lineage_id},
        outputs={"review_id": review_id}, parents=tuple(parents), created_at=created_at)


def make_session_lineage(session_id: str, review_id: str, *, review_lineage_id: str,
                         study_id: Optional[str] = None, created_at: str = DETERMINISTIC_EPOCH) -> LineageRecord:
    return make_lineage_record(
        kind="review_session", versions=review_version_bundle(),
        inputs={"review_id": review_id, "session_id": session_id, "study_id": study_id},
        outputs={"session_id": session_id}, parents=(review_lineage_id,), created_at=created_at)
