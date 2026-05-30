"""The signal (processed-EEG) registry.

No processed asset exists outside the registry. Each entry references its raw EEG
asset, case, patient, quality record, processing record, status, quality grade,
artifact counts, audit head, and lineage node. Re-registering the *same*
``(processed_id, version)`` with a *different* content signature is rejected (silent
overwrite forbidden). Mirrors ``EEGRegistry`` (NR-6).
"""

from __future__ import annotations

from ..version import SIGNAL_REGISTRY_VERSION
from ..models.domain import SignalRegistryRecord


class SignalRegistry:
    """In-memory processed-EEG registry keyed by ``processed_id``."""

    def __init__(self) -> None:
        self._records: dict[str, SignalRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}

    def register(self, record: SignalRegistryRecord) -> SignalRegistryRecord:
        key = (record.processed_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"processed asset {record.processed_id} version {record.version} already "
                "registered with different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.processed_id] = record
        return record

    def get(self, processed_id: str) -> SignalRegistryRecord:
        if processed_id not in self._records:
            raise KeyError(f"processed asset {processed_id!r} not in registry")
        return self._records[processed_id]

    def exists(self, processed_id: str) -> bool:
        return processed_id in self._records

    def list_assets(self) -> list[str]:
        return sorted(self._records)

    def by_eeg_asset(self, eeg_asset_id: str) -> list[str]:
        return sorted(pid for pid, r in self._records.items() if r.eeg_asset_id == eeg_asset_id)

    def by_case(self, case_id: str) -> list[str]:
        return sorted(pid for pid, r in self._records.items() if r.case_id == case_id)

    def by_patient(self, patient_id: str) -> list[str]:
        return sorted(pid for pid, r in self._records.items() if r.patient_id == patient_id)

    def to_dict(self) -> dict:
        return {
            "signal_registry_version": SIGNAL_REGISTRY_VERSION,
            "n_assets": len(self._records),
            "assets": {pid: r.to_dict() for pid, r in sorted(self._records.items())},
        }
