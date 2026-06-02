"""The serving registry (DRP3-H).

Tracks the serving artifacts — requests, executions, responses, contracts, and readiness
assessments — with audit + lineage references. It cross-references (and does **not**
duplicate) the shared model id + the reused inference prediction id.

**No orphan records**: every execution entry must reference a lineage node + an audit head,
its request/response/readiness must be registered, and re-registering the same
``(execution_id, version)`` with different content is rejected (silent overwrite forbidden).
"""

from __future__ import annotations

from ..models.domain import (
    EntityKind, ServingRegistryRecord, ServingRequestRecord, ServingResponseRecord,
    ServingReadinessRecord,
)
from ..version import SERVING_REGISTRY_VERSION

GENESIS = "0" * 16


class RegistryError(RuntimeError):
    """Raised on an orphan registration or a silent-overwrite attempt."""


class ServingRegistry:
    """In-memory registry of serving artifacts, keyed by id."""

    version = SERVING_REGISTRY_VERSION

    def __init__(self) -> None:
        self._requests: dict[str, ServingRequestRecord] = {}
        self._executions: dict[str, ServingRegistryRecord] = {}
        self._responses: dict[str, ServingResponseRecord] = {}
        self._readiness: dict[str, ServingReadinessRecord] = {}
        self._contracts: dict[str, str] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}

    # --- registration ---------------------------------------------------------
    def register_request(self, record: ServingRequestRecord) -> ServingRequestRecord:
        self._requests[record.request_id] = record
        return record

    def register_response(self, record: ServingResponseRecord) -> ServingResponseRecord:
        self._responses[record.response_id] = record
        return record

    def register_readiness(self, record: ServingReadinessRecord) -> ServingReadinessRecord:
        self._readiness[record.readiness_id] = record
        return record

    def register_contracts(self, contract_versions: dict) -> None:
        self._contracts.update(contract_versions)

    def register_execution(self, record: ServingRegistryRecord) -> ServingRegistryRecord:
        if not record.lineage_id:
            raise RegistryError(f"{record.execution_id!r} has no lineage node (orphans forbidden)")
        if not record.audit_state or record.audit_state == GENESIS:
            raise RegistryError(f"{record.execution_id!r} has no audit head (orphans forbidden)")
        if not (record.request_id and record.response_id and record.readiness_id):
            raise RegistryError(
                f"{record.execution_id!r} missing request/response/readiness (orphans forbidden)")
        key = (record.execution_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise RegistryError(
                f"execution {record.execution_id} v{record.version} already registered with "
                f"different content")
        self._version_sigs[key] = sig
        self._executions[record.execution_id] = record
        return record

    # --- accessors ------------------------------------------------------------
    def get_execution(self, execution_id: str) -> ServingRegistryRecord:
        if execution_id not in self._executions:
            raise KeyError(f"serving execution {execution_id!r} not in registry")
        return self._executions[execution_id]

    def exists(self, execution_id: str) -> bool:
        return execution_id in self._executions

    def list_executions(self) -> list[str]:
        return sorted(self._executions)

    def by_model(self, model_id: str) -> list[str]:
        return sorted(e for e, r in self._executions.items() if r.model_id == model_id)

    def by_status(self, status: str) -> list[str]:
        return sorted(e for e, r in self._executions.items() if r.status.value == status)

    def counts(self) -> dict:
        return {
            EntityKind.REQUEST.value: len(self._requests),
            EntityKind.EXECUTION.value: len(self._executions),
            EntityKind.RESPONSE.value: len(self._responses),
            EntityKind.READINESS.value: len(self._readiness),
            EntityKind.CONTRACT.value: len(self._contracts),
        }

    def orphans(self) -> list[str]:
        """Execution entries whose referenced request/response/readiness are not registered."""
        out = []
        for eid, r in self._executions.items():
            if (r.request_id not in self._requests or r.response_id not in self._responses
                    or r.readiness_id not in self._readiness or not r.lineage_id
                    or not r.audit_state or r.audit_state == GENESIS):
                out.append(eid)
        return sorted(out)

    def to_dict(self) -> dict:
        return {
            "serving_registry_version": self.version, "counts": self.counts(),
            "contracts": dict(sorted(self._contracts.items())),
            "requests": {r: rec.to_dict() for r, rec in sorted(self._requests.items())},
            "executions": {e: rec.to_dict() for e, rec in sorted(self._executions.items())},
            "responses": {r: rec.to_dict() for r, rec in sorted(self._responses.items())},
            "readiness": {r: rec.to_dict() for r, rec in sorted(self._readiness.items())},
        }


__all__ = ["ServingRegistry", "RegistryError"]
