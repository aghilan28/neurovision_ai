"""Simulation audit log = the shared ImmutableAuditLog bound to ``SimulationAuditRecord``.

No parallel audit system: the simulation subsystem reuses the platform's single
hash-chained :class:`ImmutableAuditLog` (V2-P1), parameterised with
:class:`SimulationAuditRecord`. Every scenario creation, simulation run, forecast
generation, comparison generation, version change, and validation event is appended
immutably.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import SimulationAuditRecord


def make_simulation_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained simulation audit log."""
    return ImmutableAuditLog(record_cls=SimulationAuditRecord)


__all__ = ["make_simulation_audit_log", "ImmutableAuditLog", "AuditError"]
