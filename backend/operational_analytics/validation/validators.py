"""Analytics validation checks + the governance gate (V3-P5).

``AnalyticsValidator`` verifies metric/health/trend/risk integrity plus
registry/audit/lineage/version integrity. ``AnalyticsGovernanceGate`` enforces the
four constitutional per-artifact validations — Architecture, Quality, Context,
Risk — before an analytics record is admitted to the registry. The "risk"
dimension enforces *derived* (the record has upstream lineage parents and source
refs) — mechanizing **analytics must never become a source of truth**.
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity
from ..models.categories import is_category
from ..models.domain import AnalyticsRecord, AnalyticsVersion

_RATIO_UNITS = frozenset({"ratio", "score"})


def _metric_problems(rec: AnalyticsRecord) -> list[str]:
    problems: list[str] = []
    for m in rec.metrics:
        # bounded metrics in [0,1]
        if m.unit in _RATIO_UNITS and m.observed and not (0.0 <= m.value <= 1.0):
            problems.append(f"{m.unit} metric {m.name} out of [0,1]")
        # trend index in [-1, 1]
        if m.unit == "index" and m.observed and not (-1.0 <= m.value <= 1.0):
            problems.append(f"index metric {m.name} out of [-1,1]")
        # unobserved metrics carry a sentinel (0.0 or -1.0), never a real value
        if not m.observed and m.value not in (0.0, -1.0):
            problems.append(f"unobserved metric {m.name} has non-sentinel value {m.value}")
        # every metric must be explainable
        if not m.explanation:
            problems.append(f"metric {m.name} has no explanation")
    return problems


def _derived_ok(rec: AnalyticsRecord) -> bool:
    """Analytics must be derived: it references upstream sources (no analytics-only truth)."""
    return len(rec.sources) > 0


class AnalyticsValidationError(RuntimeError):
    """Raised when a mandated analytics-validation check fails."""


class AnalyticsGovernanceGate:
    """The architecture/quality/context/risk gate every analytics record must pass."""

    def evaluate(self, *, record: AnalyticsRecord, parents: tuple = (),
                 requires_lineage: bool = True) -> ValidationReport:
        report = ValidationReport()
        report.add("architecture_validation", is_category(record.category),
                   f"category={record.category}")
        problems = _metric_problems(record)
        report.add("quality_validation", not problems,
                   "; ".join(problems) or "metric checks passed")
        ctx_ok = (not requires_lineage) or len(parents) > 0
        report.add("context_validation", ctx_ok,
                   "has lineage parents" if ctx_ok else "no lineage parents (untraceable)")
        derived = _derived_ok(record)
        report.add("risk_validation", derived,
                   "derived from upstream sources" if derived
                   else "not derived (analytics must never be a source of truth)")
        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise AnalyticsValidationError(f"analytics governance gate rejected: {names}")


class AnalyticsValidator:
    """Validates integrity of a registered analytics record (the eight dimensions)."""

    def validate(self, *, record: AnalyticsRecord, registry: Any, audit_log: Any,
                 lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()
        aid = record.analytics_id
        problems = _metric_problems(record)

        # metric integrity (covers metrics/health/performance/quality dimensions)
        report.add("metric_integrity", not problems, "; ".join(problems) or "ok")
        # health integrity: any health-dimension score is bounded + explainable
        health = [m for m in record.metrics if m.dimension == "health"]
        report.add("health_integrity",
                   all(0.0 <= m.value <= 1.0 for m in health if m.observed),
                   f"{len(health)} health metric(s) bounded")
        # trend integrity: every trend index in [-1, 1]
        trends = [m for m in record.metrics if m.dimension == "trend"]
        report.add("trend_integrity",
                   all(-1.0 <= m.value <= 1.0 for m in trends if m.observed),
                   f"{len(trends)} trend metric(s) in [-1,1]")
        # risk integrity: every risk score in [0, 1]
        risks = [m for m in record.metrics if m.dimension == "risk"]
        report.add("risk_integrity",
                   all(0.0 <= m.value <= 1.0 for m in risks if m.observed),
                   f"{len(risks)} risk metric(s) in [0,1]")

        try:
            rec = registry.get(aid)
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
            expected = AnalyticsVersion.compute(record.state_signature(), None)
            report.add("version_integrity", record.version == expected,
                       f"recorded={record.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        report.add("identity_integrity", validate_identity(aid)[0], f"analytics_id={aid}")
        return report
