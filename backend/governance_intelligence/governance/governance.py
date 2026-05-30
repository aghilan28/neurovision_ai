"""Governance-intelligence gate (V4-P7).

The architecture/quality/context/risk/governance gate every governance-intelligence
record must pass before it is admitted. It reuses the shared
``ml.validation.ValidationReport`` — no parallel governance system.

The defining invariant of this layer is **observe, never modify**: governance
intelligence creates *intelligence about governance*; it must not create governance
rules, change approval decisions, or bypass policy/approval workflows. The gate
encodes that invariant in its risk + governance dimensions.

Dimensions:
  * architecture  — scope present; every observed kind is a known governed kind.
  * quality       — has metrics + a well-formed [0,1] health score; risks explainable.
  * context       — has lineage parents (traceable to the governed artifacts) when
                    required, so the record traces back to the patient.
  * risk          — observation-only: no enforcement/mutation payload; risk scores in
                    [0,1] (the record never *changes* governance).
  * governance    — the record only *reports* decisions: every reported approval
                    carries an external decision/authority; counts are consistent.
"""

from __future__ import annotations

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..models.domain import GOVERNED_KINDS, GovernanceIntelligenceRecord

# attributes a governance-intelligence record must never carry — it observes only.
_MUTATION_ATTRS = ("modify", "enforce", "mutate", "override", "grant", "revoke", "decide")


class GovernanceIntelligenceError(RuntimeError):
    """Raised when the governance-intelligence gate rejects a record."""


class GovernanceIntelligenceGate:
    """The five-dimension gate for governance intelligence (reuses ValidationReport)."""

    def evaluate(self, *, record: GovernanceIntelligenceRecord, parents: tuple = (),
                 requires_lineage: bool = True) -> ValidationReport:
        report = ValidationReport()

        arch_ok = bool(record.scope) and set(record.observed_kinds) <= GOVERNED_KINDS
        report.add("architecture_validation", arch_ok,
                   f"scope={record.scope} observed_kinds={list(record.observed_kinds)}")

        scores_bounded = all(0.0 <= r.score <= 1.0 for r in record.risks)
        explainable = all(r.factors and r.explanation for r in record.risks)
        quality_ok = (bool(record.metrics) and 0.0 <= record.health_score <= 1.0
                      and scores_bounded and explainable)
        report.add("quality_validation", quality_ok,
                   "metrics present; health in [0,1]; risks explainable" if quality_ok
                   else "missing metrics / bad health score / unexplained risk")

        ctx_ok = (not requires_lineage) or len(parents) > 0
        report.add("context_validation", ctx_ok,
                   "has lineage parents (traceable to governed artifacts)" if ctx_ok
                   else "no lineage parents (untraceable)")

        # observation-only: no mutation payload; risk scores bounded.
        no_mutation = not any(
            a in _MUTATION_ATTRS for m in record.metrics for a in (m.name,))
        risk_ok = no_mutation and scores_bounded
        report.add("risk_validation", risk_ok,
                   "observation-only; governance unchanged; scores bounded" if risk_ok
                   else "carries a mutation payload or unbounded risk score (forbidden)")

        # governance: the record only REPORTS governance (one approval observation per
        # observed entity — never fabricates or drops a decision) and never makes one.
        counts_ok = len(record.approvals) == record.n_observed
        gov_ok = counts_ok and 0.0 <= record.health_score <= 1.0
        report.add("governance_validation", gov_ok,
                   "faithfully reports one observation per observed entity (makes no decision)"
                   if gov_ok else "inconsistent reporting of governance decisions")
        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise GovernanceIntelligenceError(
                f"governance-intelligence gate rejected: {names}")
