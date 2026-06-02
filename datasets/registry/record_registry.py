"""Record registry — a discoverable index of ingested EEG records.

Indexes records three ways: by ``file_id``, by ``content_sha256`` (for exact
duplicate detection — feeding :func:`datasets.validation.validate_duplicate`), and
by ``patient_id`` (the patient-disjoint primitive). The registry is deterministic
and JSON-persistable.
"""

from __future__ import annotations

import os
from typing import Any

from datasets._canonical import canonical_json
from datasets.registry.models import RegisteredRecord
from datasets.schemas.validated_record import ValidatedEegRecord

#: Schema version of the persisted record-registry file.
RECORD_REGISTRY_SCHEMA = "1.0.0"


class RecordRegistry:
    """An append/update index of ingested records, discoverable by id/hash/patient."""

    def __init__(self) -> None:
        self._by_file_id: dict[str, RegisteredRecord] = {}

    # --- registration ----------------------------------------------------
    def register(self, entry: RegisteredRecord) -> RegisteredRecord:
        """Register or update a record index entry (keyed by ``file_id``)."""
        self._by_file_id[entry.file_id] = entry
        return entry

    def register_record(self, record: ValidatedEegRecord) -> RegisteredRecord:
        """Register from a full :class:`ValidatedEegRecord` (preserving membership)."""
        existing = self._by_file_id.get(record.file_id)
        entry = RegisteredRecord.from_validated_record(record)
        if existing is not None:
            for dataset_id in existing.dataset_ids:
                entry = entry.with_dataset(dataset_id)
        return self.register(entry)

    def attach_to_dataset(self, file_id: str, dataset_id: str) -> RegisteredRecord:
        entry = self._by_file_id[file_id].with_dataset(dataset_id)
        self._by_file_id[file_id] = entry
        return entry

    # --- discovery -------------------------------------------------------
    def __contains__(self, file_id: object) -> bool:
        return file_id in self._by_file_id

    def __len__(self) -> int:
        return len(self._by_file_id)

    def get(self, file_id: str) -> RegisteredRecord:
        return self._by_file_id[file_id]

    def has_content(self, content_sha256: str) -> bool:
        return any(e.content_sha256 == content_sha256 for e in self._by_file_id.values())

    def known_sha256(self) -> frozenset[str]:
        """The set of known content hashes (for duplicate detection)."""
        return frozenset(e.content_sha256 for e in self._by_file_id.values())

    def records(self) -> tuple[RegisteredRecord, ...]:
        return tuple(self._by_file_id[k] for k in sorted(self._by_file_id))

    def patient_ids(self) -> tuple[str, ...]:
        return tuple(sorted({e.patient_id for e in self._by_file_id.values()}))

    def find_by_patient(self, patient_id: str) -> tuple[RegisteredRecord, ...]:
        return tuple(
            self._by_file_id[k]
            for k in sorted(self._by_file_id)
            if self._by_file_id[k].patient_id == patient_id
        )

    # --- persistence -----------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": RECORD_REGISTRY_SCHEMA,
            "records": [r.to_dict() for r in self.records()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecordRegistry:
        registry = cls()
        for entry in data.get("records", []):
            registry.register(RegisteredRecord.from_dict(entry))
        return registry

    def save(self, path: str | os.PathLike[str]) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(canonical_json(self.to_dict()))

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> RecordRegistry:
        import json

        with open(path, encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))
