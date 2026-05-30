"""The workflow registry: governed, versioned, traceable workflows (V3-P3).

No workflow may exist outside the registry. Re-registering the same id + version
with different content is a forbidden silent overwrite.
"""

from __future__ import annotations

from ..version import WORKFLOW_REGISTRY_VERSION
from ..models.domain import WorkflowRegistryRecord


class WorkflowRegistry:
    """In-memory registry keyed by ``workflow_id`` (latest record per workflow)."""

    def __init__(self) -> None:
        self._records: dict[str, WorkflowRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}

    def register(self, record: WorkflowRegistryRecord) -> WorkflowRegistryRecord:
        key = (record.workflow_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"workflow {record.workflow_id} version {record.version} already registered "
                "with different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.workflow_id] = record
        return record

    def get(self, workflow_id: str) -> WorkflowRegistryRecord:
        if workflow_id not in self._records:
            raise KeyError(f"workflow {workflow_id!r} not in registry")
        return self._records[workflow_id]

    def exists(self, workflow_id: str) -> bool:
        return workflow_id in self._records

    def list_workflows(self) -> list[str]:
        return sorted(self._records)

    def by_type(self, workflow_type: str) -> list[str]:
        return sorted(wid for wid, r in self._records.items() if r.workflow_type == workflow_type)

    def to_dict(self) -> dict:
        return {"workflow_registry_version": WORKFLOW_REGISTRY_VERSION,
                "n_workflows": len(self._records),
                "workflows": {wid: r.to_dict() for wid, r in sorted(self._records.items())}}
