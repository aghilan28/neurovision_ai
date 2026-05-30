"""Decision audit system.

An append-only, hash-chained, deterministic log of decision-support events
(guidance/prioritization/evidence/risk/version/registry changes). All events are
immutable. Built on the shared audit mechanism from the intelligence layer.
"""

from backend.decision_support.audit.log import DecisionAuditLog

__all__ = ["DecisionAuditLog"]
