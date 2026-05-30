"""Task governance gate (V4-P4).

The architecture/quality/context/risk/governance gate every task artifact must pass
before it is admitted (created or transitioned). It reuses the shared
``ml.validation.ValidationReport`` — no parallel governance system.

Dimensions:
  * architecture  — the task's category is in the closed taxonomy.
  * quality       — the task is explainable (title/work_definition present) + a valid priority.
  * context       — the task has lineage parents (traceable) when required, and is
                    derived from a source plan (every task derives from a plan).
  * risk          — a Task describes work; it carries no executable action payload.
  * governance    — a task may only enter READY when its governance is approved
                    (the policy-governed readiness decision, supplied by the service).
"""

from __future__ import annotations

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..taxonomy import is_category, is_priority
from ..lifecycle import TaskLifecycleState
from ..models.domain import TaskRecord

# attributes a Task must never carry — it describes work, it does not execute it.
_EXECUTION_ATTRS = ("execute", "run", "agent", "job", "process", "autonomous", "invoke")


class TaskGovernanceError(RuntimeError):
    """Raised when the task governance gate rejects an artifact."""


class TaskGovernanceGate:
    """The five-dimension gate for tasks (reuses ValidationReport)."""

    def evaluate(self, *, task: TaskRecord, parents: tuple = (), requires_lineage: bool = True,
                 target_state: TaskLifecycleState | None = None,
                 readiness_approved: bool = False) -> ValidationReport:
        report = ValidationReport()

        report.add("architecture_validation", is_category(task.category),
                   f"category={task.category}")

        quality_ok = bool(task.metadata.title and task.metadata.work_definition
                          and is_priority(task.priority))
        report.add("quality_validation", quality_ok,
                   "title + work_definition + valid priority present" if quality_ok
                   else "task not explainable (missing title/work_definition) or bad priority")

        ctx_ok = ((not requires_lineage) or len(parents) > 0) and bool(task.source_plan_id)
        report.add("context_validation", ctx_ok,
                   "has lineage parents + a source plan" if ctx_ok
                   else "no lineage parents or missing source plan (every task derives from a plan)")

        # risk: a task must carry no executable action payload (describes work only)
        no_execution = not any(a in _EXECUTION_ATTRS for a in task.metadata.tags)
        report.add("risk_validation", no_execution,
                   "describes work; no executable action payload" if no_execution
                   else "task carries an execution payload (forbidden — tasks describe work)")

        # governance: entering READY requires a policy-governed approval decision
        entering_ready = target_state == TaskLifecycleState.READY
        gov_ok = (not entering_ready) or readiness_approved
        report.add("governance_validation", gov_ok,
                   "readiness policy-approved" if gov_ok
                   else "cannot ready task without governance approval")
        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise TaskGovernanceError(f"task governance gate rejected: {names}")
