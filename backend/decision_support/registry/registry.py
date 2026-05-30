"""Decision registry.

Reuses the version-aware intelligence registry but wires in the decision-layer
audit log and lineage tracker. ``DecisionRegistryRecord`` is the decision-layer
name for a registry entry (the directive's entity).
"""

from __future__ import annotations

from backend.decision_support.audit.log import DecisionAuditLog
from backend.decision_support.lineage.tracker import DecisionLineageTracker
from backend.multi_case_intelligence.registry.registry import (
    IntelligenceRegistry,
    RegistryEntry,
)

# The directive's "DecisionRegistryRecord" entity == a shared RegistryEntry.
DecisionRegistryRecord = RegistryEntry


class DecisionRegistry(IntelligenceRegistry):
    """Version-aware registry for decision-support artifacts."""

    def __init__(self) -> None:
        super().__init__(audit_log=DecisionAuditLog(), lineage=DecisionLineageTracker())


__all__ = ["DecisionRegistry", "DecisionRegistryRecord"]
