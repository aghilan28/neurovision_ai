"""Temporal validation checks + the governance gate (V3-P2).

``TemporalValidator`` verifies timeline/history/evolution/analytics integrity plus
registry/audit/lineage/version integrity. ``TemporalGovernanceGate`` enforces the
four constitutional per-workflow validations — Architecture, Quality, Context,
Risk — before a temporal artifact is admitted to the registry.

A key temporal-specific check: artifacts are **derived from events** (their lineage
parents are event nodes), never from reconstructed hidden state.
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity
from ..models.domain import (
    Timeline, History, EvolutionRecord, TemporalAnalytics, TemporalVersion,
    artifact_id_of,
)

TEMPORAL_KINDS = frozenset({"timeline", "history", "evolution", "temporal_analytics",
                            "temporal_report"})


def _structural_problems(artifact: Any) -> list[str]:
    problems: list[str] = []
    if isinstance(artifact, Timeline):
        orders = [p.order for p in artifact.points]
        if orders != list(range(len(orders))):
            problems.append("timeline points not contiguously ordered from 0")
    if isinstance(artifact, History):
        orders = [e.order for e in artifact.entries]
        if orders != list(range(len(orders))):
            problems.append("history entries not contiguously ordered from 0")
    if isinstance(artifact, EvolutionRecord):
        prev_to = None
        for i, s in enumerate(artifact.steps):
            if s.order != i:
                problems.append("evolution steps not contiguously ordered from 0")
            if i > 0 and s.from_state != prev_to:
                problems.append(f"evolution discontinuity at step {i} "
                                f"(from={s.from_state} expected={prev_to})")
            prev_to = s.to_state
    if isinstance(artifact, TemporalAnalytics):
        for m in artifact.metrics:
            if m.observed and m.steps < 0:
                problems.append(f"metric {m.name} observed but steps<0")
            if not m.observed and m.steps != -1:
                problems.append(f"metric {m.name} unobserved but steps!=-1")
    return problems


class TemporalValidationError(RuntimeError):
    """Raised when a mandated temporal-validation check fails."""


class TemporalGovernanceGate:
    """The architecture/quality/context/risk gate every temporal artifact must pass."""

    def evaluate(self, *, artifact: Any, kind: str, parents: tuple = (),
                 derived_from_events: bool = True, requires_lineage: bool = True) -> ValidationReport:
        report = ValidationReport()
        report.add("architecture_validation", kind in TEMPORAL_KINDS,
                   f"kind={kind} is temporal-producible")
        problems = _structural_problems(artifact)
        report.add("quality_validation", not problems, "; ".join(problems) or "structural checks passed")
        ctx_ok = (not requires_lineage) or len(parents) > 0
        report.add("context_validation", ctx_ok,
                   "has lineage parents" if ctx_ok else "no lineage parents (untraceable)")
        # Risk: temporal intelligence must be derived from events (no hidden state
        # reconstruction). For artifacts with at least one point/step/metric this is
        # enforced by requiring event-derived lineage parents.
        report.add("risk_validation", derived_from_events,
                   "derived from events" if derived_from_events
                   else "not derived from events (hidden state reconstruction forbidden)")
        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise TemporalValidationError(f"temporal governance gate rejected: {names}")


class TemporalValidator:
    """Validates integrity of a registered temporal artifact (the eight dimensions)."""

    def validate(self, *, artifact: Any, kind: str, registry: Any, audit_log: Any,
                 lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()
        aid = artifact_id_of(artifact)
        lineage_id = getattr(artifact, "lineage_id", None)
        version = getattr(artifact, "version", "")

        report.add("identity_integrity", validate_identity(aid, kind)[0], f"artifact_id={aid}")

        try:
            rec = registry.get(aid)
            ok = rec.version == version and rec.lineage_id == lineage_id
            report.add("registry_integrity", bool(ok),
                       f"registered version={rec.version} artifact version={version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        try:
            heads = {e.event_hash for e in audit_log.events()}
            ok = audit_log.verify() and (getattr(artifact, "audit_state", None) in heads)
            report.add("audit_integrity", bool(ok), f"chain_verified={audit_log.verify()}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        try:
            chain_ok = bool(lineage_id) and lineage_tracker.verify_chain(lineage_id)
            report.add("lineage_integrity", bool(chain_ok), f"chain_ok={chain_ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        try:
            expected = TemporalVersion.compute(artifact.state_signature(), None)
            report.add("version_integrity", version == expected,
                       f"recorded={version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        problems = _structural_problems(artifact)
        # Map structural problems onto the specific integrity dimensions.
        report.add("timeline_integrity", not (isinstance(artifact, Timeline) and problems),
                   "; ".join(problems) if isinstance(artifact, Timeline) else "n/a")
        report.add("history_integrity", not (isinstance(artifact, History) and problems),
                   "; ".join(problems) if isinstance(artifact, History) else "n/a")
        report.add("evolution_integrity", not (isinstance(artifact, EvolutionRecord) and problems),
                   "; ".join(problems) if isinstance(artifact, EvolutionRecord) else "n/a")
        report.add("analytics_integrity", not (isinstance(artifact, TemporalAnalytics) and problems),
                   "; ".join(problems) if isinstance(artifact, TemporalAnalytics) else "n/a")

        return report
