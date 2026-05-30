"""Event validation checks + the governance gate (V3-P1).

``EventValidator`` verifies identity/registry/audit/lineage/relationship/version/
taxonomy/immutability integrity for a registered event. ``EventGovernanceGate``
enforces the four constitutional per-workflow validations — Architecture, Quality,
Context, Risk — before an event is admitted to the registry.
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity, validate_relationship_identity
from ..taxonomy import is_valid as taxonomy_is_valid
from ..models.domain import EventRecord, EventVersion
from .. import lifecycle


def _structural_problems(event: EventRecord) -> list[str]:
    problems: list[str] = []
    if not taxonomy_is_valid(event.category, event.event_type):
        problems.append(f"taxonomy pair invalid: {event.category}/{event.event_type}")
    if not validate_identity(event.event_id)[0]:
        problems.append("event_id malformed")
    if not event.metadata.source_audit_event_hash:
        problems.append("event not anchored to a source audit event (not observed)")
    if event.status not in (lifecycle.ACTIVE, lifecycle.SUPERSEDED):
        problems.append(f"invalid status {event.status!r}")
    if event.supersedes is not None and not validate_identity(event.supersedes)[0]:
        problems.append("supersedes references a malformed event id")
    return problems


class EventValidationError(RuntimeError):
    """Raised when a mandated event-validation check fails."""


class EventGovernanceGate:
    """The architecture/quality/context/risk gate every event must pass."""

    def evaluate(self, *, event: EventRecord, parents: tuple = (),
                 requires_lineage: bool = True) -> ValidationReport:
        report = ValidationReport()
        # Architecture: an event is a producible operational-event artifact with a
        # taxonomy-valid (category, type).
        report.add("architecture_validation", taxonomy_is_valid(event.category, event.event_type),
                   f"{event.category}/{event.event_type} in taxonomy")
        problems = _structural_problems(event)
        report.add("quality_validation", not problems, "; ".join(problems) or "structural checks passed")
        ctx_ok = (not requires_lineage) or len(parents) > 0
        report.add("context_validation", ctx_ok,
                   "has lineage parents" if ctx_ok else "no lineage parents (untraceable)")
        # Risk: an event must be observed (anchored to a source audit hash) and must
        # not claim to rewrite history.
        risk_problems = []
        if not event.metadata.source_audit_event_hash:
            risk_problems.append("event not anchored to source audit (would be invented)")
        report.add("risk_validation", not risk_problems, "; ".join(risk_problems) or "observed")
        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise EventValidationError(f"event governance gate rejected: {names}")


class EventValidator:
    """Validates integrity of a registered event (the eight mandated dimensions)."""

    def validate(self, *, event: EventRecord, registry: Any, audit_log: Any,
                 lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()
        eid = event.event_id

        # 1. identity integrity
        report.add("identity_integrity", validate_identity(eid)[0], f"event_id={eid}")

        # 2. registry integrity
        try:
            rec = registry.get(eid)
            ok = (rec.version == event.version and rec.lineage_id == event.lineage_id
                  and rec.status == event.status)
            report.add("registry_integrity", bool(ok),
                       f"registered version={rec.version} status={rec.status}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        # 3. audit integrity
        try:
            heads = {e.event_hash for e in audit_log.events()}
            ok = audit_log.verify() and (event.audit_state in heads)
            report.add("audit_integrity", bool(ok),
                       f"chain_verified={audit_log.verify()} audit_state_recorded={event.audit_state in heads}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # 4. lineage integrity
        try:
            chain_ok = bool(event.lineage_id) and lineage_tracker.verify_chain(event.lineage_id)
            report.add("lineage_integrity", bool(chain_ok), f"chain_ok={chain_ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # 5. relationship integrity (every relationship for this event is well-formed)
        try:
            rels = registry.relationships_for(eid)
            rel_ok = all(validate_relationship_identity(r.relationship_id)[0]
                         and r.source_event_id == eid for r in rels)
            report.add("relationship_integrity", rel_ok, f"n_relationships={len(rels)}")
        except Exception as exc:
            report.add("relationship_integrity", False, f"error: {exc}")

        # 6. version integrity
        try:
            expected = EventVersion.compute(event.state_signature(), event.supersedes)
            report.add("version_integrity", event.version == expected,
                       f"recorded={event.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        # 7. taxonomy integrity
        report.add("taxonomy_integrity", taxonomy_is_valid(event.category, event.event_type),
                   f"{event.category}/{event.event_type}")

        # 8. immutability integrity (the registry's recorded fact signature equals
        #    the event's recomputed fact signature — the fact was not rewritten)
        try:
            rec = registry.get(eid)
            report.add("immutability_integrity",
                       rec.content_signature_value == event.state_signature(),
                       "fact signature stable")
        except Exception as exc:
            report.add("immutability_integrity", False, f"error: {exc}")

        return report
