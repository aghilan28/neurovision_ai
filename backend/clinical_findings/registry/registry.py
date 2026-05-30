"""The finding registry: governed, versioned, traceable finding records."""

from __future__ import annotations

from ..version import FINDING_REGISTRY_VERSION
from ..models.domain import FindingRegistryRecord


class FindingRegistry:
    """In-memory finding registry keyed by ``finding_id`` (latest record per finding).

    A new finding *version* with the same id is an update; re-registering the *same*
    version with different content is a forbidden silent overwrite.
    """

    def __init__(self) -> None:
        self._records: dict[str, FindingRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}

    def register(self, record: FindingRegistryRecord) -> FindingRegistryRecord:
        if not record.evidence_ids:
            raise ValueError(f"finding {record.finding_id} has no evidence "
                             "(a finding must never exist without evidence)")
        key = (record.finding_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"finding {record.finding_id} version {record.version} already registered with "
                "different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.finding_id] = record
        return record

    def get(self, finding_id: str) -> FindingRegistryRecord:
        if finding_id not in self._records:
            raise KeyError(f"finding {finding_id!r} not in registry")
        return self._records[finding_id]

    def exists(self, finding_id: str) -> bool:
        return finding_id in self._records

    def list_findings(self) -> list[str]:
        return sorted(self._records)

    def by_case(self, case_id: str) -> list[str]:
        return sorted(fid for fid, r in self._records.items() if r.case_id == case_id)

    def by_review(self, review_id: str) -> list[str]:
        return sorted(fid for fid, r in self._records.items() if r.review_id == review_id)

    def to_dict(self) -> dict:
        return {
            "finding_registry_version": FINDING_REGISTRY_VERSION,
            "n_findings": len(self._records),
            "findings": {fid: r.to_dict() for fid, r in sorted(self._records.items())},
        }
