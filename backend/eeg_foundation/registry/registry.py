"""The EEG asset registry (Productization P1).

Tracks every EEG asset by id (+ version), overwrite-guarded. No EEG asset may exist
outside the registry (no orphan assets); re-registering the same id + version with
different content is a forbidden silent overwrite.
"""

from __future__ import annotations

from ..version import EEG_REGISTRY_VERSION
from ..models.domain import EEGRegistryRecord


class EEGRegistry:
    """In-memory registry keyed by ``eeg_id``."""

    def __init__(self) -> None:
        self._records: dict[str, EEGRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}

    def register(self, record: EEGRegistryRecord) -> EEGRegistryRecord:
        key = (record.eeg_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"EEG asset {record.eeg_id} version {record.version} already registered with "
                "different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.eeg_id] = record
        return record

    def get(self, eeg_id: str) -> EEGRegistryRecord:
        if eeg_id not in self._records:
            raise KeyError(f"EEG asset {eeg_id!r} not in registry")
        return self._records[eeg_id]

    def exists(self, eeg_id: str) -> bool:
        return eeg_id in self._records

    def list_assets(self) -> list:
        return sorted(self._records)

    def by_format(self, fmt: str) -> list:
        return sorted(eid for eid, r in self._records.items() if r.fmt == fmt)

    def by_case(self, case_id: str) -> list:
        return sorted(eid for eid, r in self._records.items() if r.case_id == case_id)

    def to_dict(self) -> dict:
        return {"eeg_registry_version": EEG_REGISTRY_VERSION, "n_assets": len(self._records),
                "assets": {eid: r.to_dict() for eid, r in sorted(self._records.items())}}
