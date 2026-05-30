"""Plan governance gate (V4-P3).

The architecture/quality/context/risk/governance gate every plan artifact must pass
before it is admitted (created or transitioned). It reuses the shared
``ml.validation.ValidationReport`` — no parallel governance system.

Dimensions:
  * architecture  — the plan's category is in the closed taxonomy.
  * quality       — the plan is explainable (title/approach present) + a valid priority.
  * context       — the plan has lineage parents (traceable) when required, and is
                    derived from a source goal (every plan derives from a goal).
  * risk          — a Plan is an intent structure; it carries no executable action payload.
  * governance    — a plan may only enter READY when its governance is approved
                    (the policy-governed readiness decision, supplied by the service).
"""

from __future__ import annotations

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..taxonomy import is_category, is_priority
from ..lifecycle import PlanLifecycleState
from ..models.domain import PlanRecord

# attributes a Plan must never carry — it is intent, not execution (forbidden work).
_EXECUTION_ATTRS = ("execute", "run", "agent", "job", "process", "autonomous")


class PlanGovernanceError(RuntimeError):
    """Raised when the plan governance gate rejects an artifact."""


class PlanGovernanceGate:
    """The five-dimension gate for plans (reuses ValidationReport)."""

    def evaluate(self, *, plan: PlanRecord, parents: tuple = (), requires_lineage: bool = True,
                 target_state: PlanLifecycleState | None = None,
                 readiness_approved: bool = False) -> ValidationReport:
        report = ValidationReport()

        report.add("architecture_validation", is_category(plan.category),
                   f"category={plan.category}")

        quality_ok = bool(plan.metadata.title and plan.metadata.approach
                          and is_priority(plan.priority))
        report.add("quality_validation", quality_ok,
                   "title + approach + valid priority present" if quality_ok
                   else "plan not explainable (missing title/approach) or bad priority")

        ctx_ok = ((not requires_lineage) or len(parents) > 0) and bool(plan.source_goal_id)
        report.add("context_validation", ctx_ok,
                   "has lineage parents + a source goal" if ctx_ok
                   else "no lineage parents or missing source goal (every plan derives from a goal)")

        # risk: a plan must carry no executable action payload (intent, not execution)
        no_execution = not any(a in _EXECUTION_ATTRS for a in plan.metadata.tags)
        report.add("risk_validation", no_execution,
                   "intent structure; no executable action payload" if no_execution
                   else "plan carries an execution payload (forbidden — plans are intent)")

        # governance: entering READY requires a policy-governed approval decision
        entering_ready = target_state == PlanLifecycleState.READY
        gov_ok = (not entering_ready) or readiness_approved
        report.add("governance_validation", gov_ok,
                   "readiness policy-approved" if gov_ok
                   else "cannot ready plan without governance approval")
        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise PlanGovernanceError(f"plan governance gate rejected: {names}")
