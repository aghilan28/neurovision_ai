"""Workflow validation checks + the governance gate (V3-P3).

``WorkflowValidator`` verifies transition/dependency/metric integrity plus
registry/audit/lineage/version integrity. ``WorkflowGovernanceGate`` enforces the
four constitutional per-workflow validations — Architecture, Quality, Context,
Risk — before a workflow is admitted to the registry. The "risk" dimension enforces
*derived from events* (no hidden workflow state).
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity
from ..models.domain import WorkflowRecord, WorkflowVersion

WORKFLOW_KINDS = frozenset({"workflow"})
_DEP_RELATIONS = frozenset({"upstream", "downstream", "blocked", "waiting", "completed"})


def _structural_problems(wf: WorkflowRecord) -> list[str]:
    problems: list[str] = []
    # transitions contiguously ordered + continuous
    prev_to = None
    for i, t in enumerate(wf.transitions):
        if t.order != i:
            problems.append("transitions not contiguously ordered from 0")
        if i > 0 and t.from_state != prev_to:
            problems.append(f"transition discontinuity at {i} (from={t.from_state} expected={prev_to})")
        prev_to = t.to_state
    # dependency relations valid
    for d in wf.dependencies:
        if d.relation not in _DEP_RELATIONS:
            problems.append(f"invalid dependency relation {d.relation!r}")
    # metric values finite + ratios bounded
    for m in wf.metrics:
        if m.unit == "ratio" and not (0.0 <= m.value <= 1.0):
            problems.append(f"ratio metric {m.name} out of [0,1]")
        if not m.observed and m.value not in (0.0, -1.0):
            problems.append(f"unobserved metric {m.name} has non-zero value")
    # the latest state must equal the last transition's to_state (or 'empty')
    expected_state = wf.transitions[-1].to_state if wf.transitions else "empty"
    if wf.state != expected_state:
        problems.append(f"workflow state {wf.state!r} != last transition {expected_state!r}")
    return problems


class WorkflowValidationError(RuntimeError):
    """Raised when a mandated workflow-validation check fails."""


class WorkflowGovernanceGate:
    """The architecture/quality/context/risk gate every workflow must pass."""

    def evaluate(self, *, workflow: WorkflowRecord, parents: tuple = (),
                 derived_from_events: bool = True, requires_lineage: bool = True) -> ValidationReport:
        report = ValidationReport()
        report.add("architecture_validation", "workflow" in WORKFLOW_KINDS, "kind=workflow")
        problems = _structural_problems(workflow)
        report.add("quality_validation", not problems, "; ".join(problems) or "structural checks passed")
        ctx_ok = (not requires_lineage) or len(parents) > 0
        report.add("context_validation", ctx_ok,
                   "has lineage parents" if ctx_ok else "no lineage parents (untraceable)")
        report.add("risk_validation", derived_from_events,
                   "derived from events" if derived_from_events
                   else "not derived from events (hidden workflow state forbidden)")
        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise WorkflowValidationError(f"workflow governance gate rejected: {names}")


class WorkflowValidator:
    """Validates integrity of a registered workflow (the seven dimensions)."""

    def validate(self, *, workflow: WorkflowRecord, registry: Any, audit_log: Any,
                 lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()
        wid = workflow.workflow_id
        problems = _structural_problems(workflow)

        report.add("transition_integrity",
                   not [p for p in problems if "transition" in p],
                   "; ".join(p for p in problems if "transition" in p) or "ok")
        report.add("dependency_integrity",
                   not [p for p in problems if "dependency" in p],
                   "; ".join(p for p in problems if "dependency" in p) or "ok")
        report.add("metric_integrity",
                   not [p for p in problems if "metric" in p],
                   "; ".join(p for p in problems if "metric" in p) or "ok")

        try:
            rec = registry.get(wid)
            ok = rec.version == workflow.version and rec.lineage_id == workflow.lineage_id
            report.add("registry_integrity", bool(ok),
                       f"registered version={rec.version} workflow version={workflow.version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        try:
            heads = {e.event_hash for e in audit_log.events()}
            ok = audit_log.verify() and (workflow.audit_state in heads)
            report.add("audit_integrity", bool(ok), f"chain_verified={audit_log.verify()}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        try:
            chain_ok = bool(workflow.lineage_id) and lineage_tracker.verify_chain(workflow.lineage_id)
            report.add("lineage_integrity", bool(chain_ok), f"chain_ok={chain_ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        try:
            expected = WorkflowVersion.compute(workflow.state_signature(), None)
            report.add("version_integrity", workflow.version == expected,
                       f"recorded={workflow.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        report.add("identity_integrity", validate_identity(wid)[0], f"workflow_id={wid}")
        return report
