"""The case registry: governed, versioned, traceable case records."""

from __future__ import annotations

from ..version import CASE_REGISTRY_VERSION
from ..models.domain import CaseRegistryRecord


class CaseRegistry:
    """In-memory case registry keyed by ``case_id``.

    The registry holds the latest registry record per case. Updates (e.g. a new
    case version after a lifecycle transition) are expressed as a new record with
    the same ``case_id`` and an incremented ``version`` — that is an *update*, not a
    silent overwrite, so it is permitted. Re-registering the *same* ``version`` with
    a *different* content signature is forbidden.
    """

    def __init__(self) -> None:
        self._records: dict[str, CaseRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}  # (case_id, version) -> sig

    def register(self, record: CaseRegistryRecord) -> CaseRegistryRecord:
        key = (record.case_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"case {record.case_id} version {record.version} already registered with "
                "different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.case_id] = record
        return record

    def get(self, case_id: str) -> CaseRegistryRecord:
        if case_id not in self._records:
            raise KeyError(f"case {case_id!r} not in registry")
        return self._records[case_id]

    def exists(self, case_id: str) -> bool:
        return case_id in self._records

    def list_cases(self) -> list[str]:
        return sorted(self._records)

    def by_patient(self, patient_id: str) -> list[str]:
        return sorted(cid for cid, r in self._records.items() if r.patient_id == patient_id)

    def to_dict(self) -> dict:
        return {
            "case_registry_version": CASE_REGISTRY_VERSION,
            "n_cases": len(self._records),
            "cases": {cid: r.to_dict() for cid, r in sorted(self._records.items())},
        }
