"""The EEG asset registry: governed, versioned, traceable EEG records.

No EEG asset may exist outside the registry. Each asset is registered with its
case/patient, format, status, validation/storage/metadata state, owner, creation
date, audit head, lineage reference, and dependencies. Re-registering the *same*
``(asset_id, version)`` with a *different* content signature is rejected (silent
overwrite forbidden); a new version of the same asset is a legitimate update.

Mirrors ``backend.clinical_cases.registry.CaseRegistry`` (NR-6).
"""

from __future__ import annotations

from ..version import EEG_REGISTRY_VERSION
from ..models.domain import EEGRegistryRecord


class EEGRegistry:
    """In-memory EEG asset registry keyed by ``asset_id``."""

    def __init__(self) -> None:
        self._records: dict[str, EEGRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}  # (asset_id, version) -> sig

    def register(self, record: EEGRegistryRecord) -> EEGRegistryRecord:
        key = (record.asset_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"EEG asset {record.asset_id} version {record.version} already registered with "
                "different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.asset_id] = record
        return record

    def get(self, asset_id: str) -> EEGRegistryRecord:
        if asset_id not in self._records:
            raise KeyError(f"EEG asset {asset_id!r} not in registry")
        return self._records[asset_id]

    def exists(self, asset_id: str) -> bool:
        return asset_id in self._records

    def list_assets(self) -> list[str]:
        return sorted(self._records)

    def by_case(self, case_id: str) -> list[str]:
        return sorted(aid for aid, r in self._records.items() if r.case_id == case_id)

    def by_patient(self, patient_id: str) -> list[str]:
        return sorted(aid for aid, r in self._records.items() if r.patient_id == patient_id)

    def to_dict(self) -> dict:
        return {
            "eeg_registry_version": EEG_REGISTRY_VERSION,
            "n_assets": len(self._records),
            "assets": {aid: r.to_dict() for aid, r in sorted(self._records.items())},
        }
