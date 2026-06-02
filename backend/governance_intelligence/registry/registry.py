"""The governance-intelligence registry (V4-P7).

Tracks every admitted governance-intelligence record (by id + version) plus flat
indexes of the approvals, violations, escalations, risks, and metrics it surfaced —
so the workstation and reports can look them up without recomputation. No record may
exist outside the registry; re-registering the same id + version with different
content is a forbidden silent overwrite.
"""

from __future__ import annotations

from ..version import GOVERNANCE_REGISTRY_VERSION
from ..models.domain import GovernanceRegistryRecord


class GovernanceRegistry:
    """In-memory registry keyed by ``intelligence_id`` (+ flattened sub-indexes)."""

    def __init__(self) -> None:
        self._records: dict[str, GovernanceRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}
        self._approvals: dict[str, dict] = {}
        self._violations: dict[str, dict] = {}
        self._escalations: dict[str, dict] = {}
        self._risks: dict[str, dict] = {}
        self._metrics: dict[str, dict] = {}

    # --- intelligence records -------------------------------------------------
    def register(self, record: GovernanceRegistryRecord) -> GovernanceRegistryRecord:
        key = (record.intelligence_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"governance-intelligence {record.intelligence_id} version {record.version} "
                "already registered with different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.intelligence_id] = record
        return record

    def index(self, record) -> None:
        """Index an admitted aggregate's sub-records for lookup (idempotent)."""
        for a in record.approvals:
            self._approvals[a.approval_id] = a.to_dict()
        for v in record.violations:
            self._violations[v.violation_id] = v.to_dict()
        for e in record.escalations:
            self._escalations[e.escalation_id] = e.to_dict()
        for r in record.risks:
            self._risks[r.risk_id] = r.to_dict()
        for m in record.metrics:
            self._metrics[m.name] = m.to_dict()

    def get(self, intelligence_id: str) -> GovernanceRegistryRecord:
        if intelligence_id not in self._records:
            raise KeyError(f"governance-intelligence {intelligence_id!r} not in registry")
        return self._records[intelligence_id]

    def exists(self, intelligence_id: str) -> bool:
        return intelligence_id in self._records

    def list_intelligence(self) -> list[str]:
        return sorted(self._records)

    def list_approvals(self) -> list[str]:
        return sorted(self._approvals)

    def list_violations(self) -> list[str]:
        return sorted(self._violations)

    def list_escalations(self) -> list[str]:
        return sorted(self._escalations)

    def list_risks(self) -> list[str]:
        return sorted(self._risks)

    def list_metrics(self) -> list[str]:
        return sorted(self._metrics)

    def to_dict(self) -> dict:
        return {"governance_registry_version": GOVERNANCE_REGISTRY_VERSION,
                "n_intelligence": len(self._records), "n_approvals": len(self._approvals),
                "n_violations": len(self._violations), "n_escalations": len(self._escalations),
                "n_risks": len(self._risks), "n_metrics": len(self._metrics),
                "intelligence": {iid: r.to_dict()
                                 for iid, r in sorted(self._records.items())},
                "approvals": dict(sorted(self._approvals.items())),
                "violations": dict(sorted(self._violations.items())),
                "escalations": dict(sorted(self._escalations.items())),
                "risks": dict(sorted(self._risks.items())),
                "metrics": dict(sorted(self._metrics.items()))}
