"""Execution governance gate (V4-P6).

The architecture/quality/context/risk/governance gate every execution artifact must
pass before it is admitted (created or transitioned). It reuses the shared
``ml.validation.ValidationReport`` — no parallel governance system.

Dimensions:
  * architecture  — the execution references a complete coordination context.
  * quality       — explainable (title/objective present); the referenced assignment
                    is consistent with the context.
  * context       — the execution has lineage parents (traceable) when required, and
                    references an approved agent assignment.
  * risk          — execution carries no autonomous/self-directed payload; it
                    coordinates approved work only (no autonomous planning).
  * governance    — an execution may only become ACTIVE when authorized
                    (the policy-governed activation decision, supplied by the service).
"""

from __future__ import annotations

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..lifecycle import ExecutionLifecycleState
from ..coordination import context_complete, assignment_consistent
from ..models.domain import ExecutionRecord

# attributes an Execution must never carry — it is governed progression, not freedom.
_AUTONOMY_ATTRS = ("autonomous", "self_directed", "self-directed", "agent_freedom", "unbounded",
                   "plan")


class ExecutionGovernanceError(RuntimeError):
    """Raised when the execution governance gate rejects an artifact."""


class ExecutionGovernanceGate:
    """The five-dimension gate for executions (reuses ValidationReport)."""

    def evaluate(self, *, execution: ExecutionRecord, parents: tuple = (),
                 requires_lineage: bool = True, target_state: ExecutionLifecycleState | None = None,
                 authorization_approved: bool = False) -> ValidationReport:
        report = ValidationReport()

        ctx_ok, missing = context_complete(execution.context)
        report.add("architecture_validation", ctx_ok,
                   "coordination context complete" if ctx_ok else f"missing context: {missing}")

        consistent, why = assignment_consistent(execution.context, execution.assignment)
        quality_ok = bool(execution.metadata.title and execution.metadata.objective) and consistent
        report.add("quality_validation", quality_ok,
                   "title + objective present; assignment consistent" if quality_ok
                   else f"not explainable or assignment inconsistent ({why})")

        has_assignment = bool(execution.assignment.assignment_id)
        lineage_ok = (not requires_lineage) or len(parents) > 0
        ctx_ref_ok = lineage_ok and has_assignment
        report.add("context_validation", ctx_ref_ok,
                   "has lineage parents + references an approved assignment" if ctx_ref_ok
                   else "no lineage parents or missing assignment reference")

        # risk: no autonomy/self-direction payload (governed progression only)
        no_autonomy = not any(a in _AUTONOMY_ATTRS for a in execution.metadata.tags)
        report.add("risk_validation", no_autonomy,
                   "governed progression; no autonomous payload" if no_autonomy
                   else "execution carries an autonomy/self-direction payload (forbidden)")

        # governance: entering ACTIVE requires a policy-governed authorization decision
        entering_active = target_state == ExecutionLifecycleState.ACTIVE
        gov_ok = (not entering_active) or authorization_approved
        report.add("governance_validation", gov_ok,
                   "activation authorized" if gov_ok
                   else "cannot activate execution without authorization")
        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise ExecutionGovernanceError(f"execution governance gate rejected: {names}")
