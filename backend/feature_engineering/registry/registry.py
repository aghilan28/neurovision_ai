"""The feature-asset registry.

No feature asset exists outside the registry. Each entry references its processed
asset, the EEG asset, case, patient, families/groups present, feature counts,
status, audit head, and lineage node. Re-registering the *same*
``(feature_asset_id, version)`` with a *different* content signature is rejected
(silent overwrite forbidden). Mirrors ``SignalRegistry`` (NR-6).
"""

from __future__ import annotations

from ..version import FEATURE_REGISTRY_VERSION
from ..models.domain import FeatureRegistryRecord


class FeatureRegistry:
    """In-memory feature-asset registry keyed by ``feature_asset_id``."""

    def __init__(self) -> None:
        self._records: dict[str, FeatureRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}

    def register(self, record: FeatureRegistryRecord) -> FeatureRegistryRecord:
        key = (record.feature_asset_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"feature asset {record.feature_asset_id} version {record.version} already "
                "registered with different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.feature_asset_id] = record
        return record

    def get(self, feature_asset_id: str) -> FeatureRegistryRecord:
        if feature_asset_id not in self._records:
            raise KeyError(f"feature asset {feature_asset_id!r} not in registry")
        return self._records[feature_asset_id]

    def exists(self, feature_asset_id: str) -> bool:
        return feature_asset_id in self._records

    def list_assets(self) -> list[str]:
        return sorted(self._records)

    def by_processed(self, processed_id: str) -> list[str]:
        return sorted(fid for fid, r in self._records.items() if r.processed_id == processed_id)

    def by_case(self, case_id: str) -> list[str]:
        return sorted(fid for fid, r in self._records.items() if r.case_id == case_id)

    def by_patient(self, patient_id: str) -> list[str]:
        return sorted(fid for fid, r in self._records.items() if r.patient_id == patient_id)

    def by_family(self, family: str) -> list[str]:
        return sorted(fid for fid, r in self._records.items() if family in r.families)

    def to_dict(self) -> dict:
        return {
            "feature_registry_version": FEATURE_REGISTRY_VERSION,
            "n_assets": len(self._records),
            "assets": {fid: r.to_dict() for fid, r in sorted(self._records.items())},
        }
