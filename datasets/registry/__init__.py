"""``datasets.registry`` — discoverable registries for records and datasets.

Makes **every record and dataset discoverable** (Project directive). Two
deterministic, JSON-backed stores:

* :class:`~datasets.registry.record_registry.RecordRegistry` — indexes ingested
  records by ``file_id`` and ``content_sha256`` (the latter powers exact
  duplicate detection) and by ``patient_id`` (the patient-disjoint primitive).
* :class:`~datasets.registry.dataset_registry.DatasetRegistry` — tracks datasets
  with their version, source, status, validation/quality state, dependencies,
  owner, and lineage reference.

Persistence is canonical JSON (stable ordering) so a registry file is reproducible
and diff-friendly (AP-6/NR-10).
"""

from __future__ import annotations

from datasets.registry.dataset_registry import DatasetRegistry, RegistryError
from datasets.registry.models import RegisteredDataset, RegisteredRecord
from datasets.registry.record_registry import RecordRegistry

__all__ = [
    "DatasetRegistry",
    "RecordRegistry",
    "RegisteredDataset",
    "RegisteredRecord",
    "RegistryError",
]
