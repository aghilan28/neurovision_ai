"""The analytics registry: governed, versioned, traceable analytics (V3-P5).

No analytics artifact may exist outside the registry. Re-registering the same id +
version with different content is a forbidden silent overwrite. The registry tracks
metrics/health/trend/risk records, their versions, and their audit + lineage
references — analytics is derived intelligence, but it is still fully governed.
"""

from __future__ import annotations

from ..version import ANALYTICS_REGISTRY_VERSION
from ..models.domain import AnalyticsRegistryRecord


class AnalyticsRegistry:
    """In-memory registry keyed by ``analytics_id`` (latest record per artifact)."""

    def __init__(self) -> None:
        self._records: dict[str, AnalyticsRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}

    def register(self, record: AnalyticsRegistryRecord) -> AnalyticsRegistryRecord:
        key = (record.analytics_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"analytics {record.analytics_id} version {record.version} already registered "
                "with different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.analytics_id] = record
        return record

    def get(self, analytics_id: str) -> AnalyticsRegistryRecord:
        if analytics_id not in self._records:
            raise KeyError(f"analytics {analytics_id!r} not in registry")
        return self._records[analytics_id]

    def exists(self, analytics_id: str) -> bool:
        return analytics_id in self._records

    def list_analytics(self) -> list[str]:
        return sorted(self._records)

    def by_category(self, category: str) -> list[str]:
        return sorted(aid for aid, r in self._records.items() if r.category == category)

    def to_dict(self) -> dict:
        return {"analytics_registry_version": ANALYTICS_REGISTRY_VERSION,
                "n_analytics": len(self._records),
                "analytics": {aid: r.to_dict() for aid, r in sorted(self._records.items())}}
