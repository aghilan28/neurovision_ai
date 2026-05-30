"""Recommendation validation checks + the governance gate (V3-P6).

``RecommendationValidator`` verifies context/evidence/priority/guidance integrity
plus registry/audit/lineage/version integrity. ``RecommendationGovernanceGate``
enforces the four constitutional per-artifact validations — Architecture, Quality,
Context, Risk — before a recommendation is admitted. The "risk" dimension enforces
that every recommendation is **evidence-linked AND analytics-linked** — mechanizing
*no black-box recommendations*.
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity
from ..models.kinds import is_kind, is_priority
from ..models.domain import RecommendationRecord, RecommendationVersion


def _quality_problems(rec: RecommendationRecord) -> list[str]:
    problems: list[str] = []
    if not rec.statement:
        problems.append("recommendation has no statement (not explainable)")
    if not rec.rationale:
        problems.append("recommendation has no rationale (not explainable)")
    p = rec.priority
    if not is_priority(p.level):
        problems.append(f"invalid priority level {p.level!r}")
    if not (0.0 <= p.score <= 1.0):
        problems.append(f"priority score {p.score} out of [0,1]")
    if not p.reason:
        problems.append("priority has no reason (not explainable)")
    # every evidence item must reference a real source
    for e in rec.evidence:
        if not e.source_id or not e.source_kind:
            problems.append("evidence item missing source reference")
    return problems


def _evidence_linked(rec: RecommendationRecord) -> bool:
    return len(rec.evidence) > 0


def _analytics_linked(rec: RecommendationRecord) -> bool:
    has_ids = len(rec.analytics_ids) > 0
    has_ev = any(e.source_kind == "analytics" for e in rec.evidence)
    return has_ids and has_ev


class RecommendationValidationError(RuntimeError):
    """Raised when a mandated recommendation-validation check fails."""


class RecommendationGovernanceGate:
    """The architecture/quality/context/risk gate every recommendation must pass."""

    def evaluate(self, *, record: RecommendationRecord, parents: tuple = (),
                 requires_lineage: bool = True) -> ValidationReport:
        report = ValidationReport()
        report.add("architecture_validation", is_kind(record.kind), f"kind={record.kind}")
        problems = _quality_problems(record)
        report.add("quality_validation", not problems,
                   "; ".join(problems) or "explainability + priority checks passed")
        ctx_ok = (not requires_lineage) or len(parents) > 0
        report.add("context_validation", ctx_ok,
                   "has lineage parents" if ctx_ok else "no lineage parents (untraceable)")
        evidence_linked = _evidence_linked(record)
        analytics_linked = _analytics_linked(record)
        risk_ok = evidence_linked and analytics_linked
        report.add("risk_validation", risk_ok,
                   "evidence-linked + analytics-linked" if risk_ok
                   else ("not evidence-linked" if not evidence_linked
                         else "not analytics-linked") + " (black-box recommendation forbidden)")
        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise RecommendationValidationError(
                f"recommendation governance gate rejected: {names}")



class RecommendationValidator:
    """Validates integrity of a registered recommendation (the eight dimensions)."""

    def validate(self, *, record: RecommendationRecord, registry: Any, audit_log: Any,
                 lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()
        rid = record.recommendation_id

        # context integrity: the cited context exists in the registry (if set)
        try:
            ctx_ok = (record.context_id is None) or registry.has_context(record.context_id)
            report.add("context_integrity", bool(ctx_ok),
                       f"context_id={record.context_id}")
        except Exception as exc:
            report.add("context_integrity", False, f"error: {exc}")

        # evidence integrity: evidence present + each references a real source
        ev_ok = len(record.evidence) > 0 and all(e.source_id and e.source_kind
                                                  for e in record.evidence)
        report.add("evidence_integrity", bool(ev_ok),
                   f"{record.n_evidence} evidence item(s)")

        # priority integrity: level valid + score banded consistently
        from ..prioritization import level_for_score
        p = record.priority
        prio_ok = (is_priority(p.level) and 0.0 <= p.score <= 1.0
                   and level_for_score(p.score) == p.level)
        report.add("priority_integrity", bool(prio_ok),
                   f"level={p.level} score={p.score}")

        # guidance integrity: statement + rationale present (explainable)
        report.add("guidance_integrity", bool(record.statement and record.rationale),
                   "statement + rationale present")

        try:
            rec = registry.get(rid)
            ok = rec.version == record.version and rec.lineage_id == record.lineage_id
            report.add("registry_integrity", bool(ok),
                       f"registered version={rec.version} record version={record.version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        try:
            heads = {e.event_hash for e in audit_log.events()}
            ok = audit_log.verify() and (record.audit_state in heads)
            report.add("audit_integrity", bool(ok), f"chain_verified={audit_log.verify()}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        try:
            chain_ok = bool(record.lineage_id) and lineage_tracker.verify_chain(record.lineage_id)
            report.add("lineage_integrity", bool(chain_ok), f"chain_ok={chain_ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        try:
            expected = RecommendationVersion.compute(record.state_signature(), None)
            report.add("version_integrity", record.version == expected,
                       f"recorded={record.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        report.add("identity_integrity", validate_identity(rid)[0], f"recommendation_id={rid}")
        return report
