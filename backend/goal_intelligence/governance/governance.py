"""Goal governance gate (V4-P1).

The architecture/quality/context/risk/governance gate every goal artifact must pass
before it is admitted (created or transitioned). It reuses the shared
``ml.validation.ValidationReport`` — no parallel governance system.

Dimensions:
  * architecture  — the goal's category is in the closed taxonomy.
  * quality       — the goal is explainable (title/desired outcome present) + a valid priority.
  * context       — the goal has lineage parents (traceable) when required.
  * risk          — a Goal is intent only; it carries no executable action payload.
  * governance    — a goal may only enter ACTIVE when its governance is approved
                    (the policy-governed activation decision, supplied by the service).
"""

from __future__ import annotations

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..taxonomy import is_category, is_priority
from ..lifecycle import GoalLifecycleState
from ..models.domain import GoalRecord

# attributes a Goal must never carry — it is intent, not execution (forbidden work).
_EXECUTION_ATTRS = ("action", "command", "execute", "task", "plan", "agent", "run")


class GoalGovernanceError(RuntimeError):
    """Raised when the goal governance gate rejects an artifact."""


class GoalGovernanceGate:
    """The five-dimension gate for goals (reuses ValidationReport)."""

    def evaluate(self, *, goal: GoalRecord, parents: tuple = (), requires_lineage: bool = True,
                 target_state: GoalLifecycleState | None = None,
                 activation_approved: bool = False) -> ValidationReport:
        report = ValidationReport()

        report.add("architecture_validation", is_category(goal.category),
                   f"category={goal.category}")

        quality_ok = bool(goal.metadata.title and goal.metadata.desired_outcome
                          and is_priority(goal.priority))
        report.add("quality_validation", quality_ok,
                   "title + desired_outcome + valid priority present" if quality_ok
                   else "goal not explainable (missing title/outcome) or bad priority")

        ctx_ok = (not requires_lineage) or len(parents) > 0
        report.add("context_validation", ctx_ok,
                   "has lineage parents" if ctx_ok else "no lineage parents (untraceable)")

        # risk: a goal must carry no executable action payload (intent, not execution)
        no_execution = not any(a in _EXECUTION_ATTRS for a in goal.metadata.tags)
        report.add("risk_validation", no_execution,
                   "intent only; no executable action payload" if no_execution
                   else "goal carries an execution payload (forbidden — goals are intent)")

        # governance: entering ACTIVE requires a policy-governed approval decision
        entering_active = target_state == GoalLifecycleState.ACTIVE
        gov_ok = (not entering_active) or activation_approved
        report.add("governance_validation", gov_ok,
                   "activation policy-approved" if gov_ok
                   else "cannot activate goal without governance approval")
        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise GoalGovernanceError(f"goal governance gate rejected: {names}")
