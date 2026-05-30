"""The review registry: governed, versioned, traceable review records."""

from __future__ import annotations

from ..version import REVIEW_REGISTRY_VERSION
from ..models.domain import ReviewRegistryRecord


class ReviewRegistry:
    """In-memory review registry keyed by ``review_id`` (latest record per review).

    A new review *version* with the same ``review_id`` is an update; re-registering
    the *same* ``version`` with different content is a forbidden silent overwrite.
    """

    def __init__(self) -> None:
        self._records: dict[str, ReviewRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}

    def register(self, record: ReviewRegistryRecord) -> ReviewRegistryRecord:
        key = (record.review_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"review {record.review_id} version {record.version} already registered with "
                "different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.review_id] = record
        return record

    def get(self, review_id: str) -> ReviewRegistryRecord:
        if review_id not in self._records:
            raise KeyError(f"review {review_id!r} not in registry")
        return self._records[review_id]

    def exists(self, review_id: str) -> bool:
        return review_id in self._records

    def list_reviews(self) -> list[str]:
        return sorted(self._records)

    def by_case(self, case_id: str) -> list[str]:
        return sorted(rid for rid, r in self._records.items() if r.case_id == case_id)

    def to_dict(self) -> dict:
        return {
            "review_registry_version": REVIEW_REGISTRY_VERSION,
            "n_reviews": len(self._records),
            "reviews": {rid: r.to_dict() for rid, r in sorted(self._records.items())},
        }
