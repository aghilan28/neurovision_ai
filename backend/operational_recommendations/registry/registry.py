"""The recommendation registry: governed, versioned, traceable records (V3-P6).

No recommendation may exist outside the registry. Re-registering the same id +
version with different content is a forbidden silent overwrite. The registry tracks
recommendations, guidance, priorities, escalations, contexts, versions, and their
audit + lineage references.
"""

from __future__ import annotations

from ..version import RECOMMENDATION_REGISTRY_VERSION
from ..models.domain import RecommendationRegistryRecord, RecommendationContext


class RecommendationRegistry:
    """In-memory registry keyed by ``recommendation_id`` (+ a context store)."""

    def __init__(self) -> None:
        self._records: dict[str, RecommendationRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}
        self._contexts: dict[str, RecommendationContext] = {}

    # --- recommendations ------------------------------------------------------
    def register(self, record: RecommendationRegistryRecord) -> RecommendationRegistryRecord:
        key = (record.recommendation_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"recommendation {record.recommendation_id} version {record.version} already "
                "registered with different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.recommendation_id] = record
        return record

    def get(self, recommendation_id: str) -> RecommendationRegistryRecord:
        if recommendation_id not in self._records:
            raise KeyError(f"recommendation {recommendation_id!r} not in registry")
        return self._records[recommendation_id]

    def exists(self, recommendation_id: str) -> bool:
        return recommendation_id in self._records

    def list_recommendations(self) -> list[str]:
        return sorted(self._records)

    def by_kind(self, kind: str) -> list[str]:
        return sorted(rid for rid, r in self._records.items() if r.kind == kind)

    def by_priority(self, level: str) -> list[str]:
        return sorted(rid for rid, r in self._records.items() if r.priority_level == level)

    # --- contexts -------------------------------------------------------------
    def register_context(self, context: RecommendationContext) -> RecommendationContext:
        existing = self._contexts.get(context.context_id)
        if existing is not None and existing.state_signature() != context.state_signature():
            raise ValueError(f"context {context.context_id} already registered with "
                             "different content (silent overwrite forbidden)")
        self._contexts[context.context_id] = context
        return context

    def context(self, context_id: str) -> RecommendationContext:
        if context_id not in self._contexts:
            raise KeyError(f"context {context_id!r} not in registry")
        return self._contexts[context_id]

    def has_context(self, context_id: str) -> bool:
        return context_id in self._contexts

    def list_contexts(self) -> list[str]:
        return sorted(self._contexts)

    def to_dict(self) -> dict:
        return {"recommendation_registry_version": RECOMMENDATION_REGISTRY_VERSION,
                "n_recommendations": len(self._records), "n_contexts": len(self._contexts),
                "recommendations": {rid: r.to_dict() for rid, r in sorted(self._records.items())},
                "contexts": {cid: c.to_dict() for cid, c in sorted(self._contexts.items())}}
