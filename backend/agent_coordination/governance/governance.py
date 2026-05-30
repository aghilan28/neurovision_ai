"""Agent governance gate (V4-P5).

The architecture/quality/context/risk/governance gate every agent artifact must pass
before it is admitted (created or transitioned). It reuses the shared
``ml.validation.ValidationReport`` — no parallel governance system.

Dimensions:
  * architecture  — the agent's category is in the closed taxonomy.
  * quality       — the agent is explainable (title/role present) + a valid priority;
                    every capability dependency the agent declares is also declared.
  * context       — the agent has lineage parents (traceable) when required.
  * risk          — an Agent describes capability and holds no autonomous authority
                    (no execution payload); high/critical-risk capabilities must be
                    capability-approved before the agent may become AVAILABLE.
  * governance    — an agent may only become AVAILABLE when its governance is approved
                    (the policy-governed availability decision, supplied by the service).
"""

from __future__ import annotations

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..taxonomy import is_category, is_priority
from ..lifecycle import AgentLifecycleState
from ..capabilities import unmet_dependencies, high_risk_unapproved
from ..models.domain import AgentRecord

# attributes an Agent must never carry — it describes capability, holds no authority.
_AUTONOMY_ATTRS = ("autonomous", "self_modify", "self-modify", "unbounded", "execute", "run")


class AgentGovernanceError(RuntimeError):
    """Raised when the agent governance gate rejects an artifact."""


class AgentGovernanceGate:
    """The five-dimension gate for agents (reuses ValidationReport)."""

    def evaluate(self, *, agent: AgentRecord, parents: tuple = (), requires_lineage: bool = True,
                 target_state: AgentLifecycleState | None = None,
                 availability_approved: bool = False) -> ValidationReport:
        report = ValidationReport()

        report.add("architecture_validation", is_category(agent.category),
                   f"category={agent.category}")

        unmet = unmet_dependencies(agent)
        quality_ok = bool(agent.metadata.title and agent.metadata.role
                          and is_priority(agent.priority)) and not unmet
        report.add("quality_validation", quality_ok,
                   "title + role + valid priority; capability dependencies declared" if quality_ok
                   else f"not explainable / bad priority / unmet capability deps: {unmet}")

        ctx_ok = (not requires_lineage) or len(parents) > 0
        report.add("context_validation", ctx_ok,
                   "has lineage parents" if ctx_ok else "no lineage parents (untraceable)")

        # risk: no autonomous-authority payload; high-risk capabilities approved before AVAILABLE
        no_autonomy = not any(a in _AUTONOMY_ATTRS for a in agent.metadata.tags)
        unapproved = high_risk_unapproved(agent)
        entering_available = target_state == AgentLifecycleState.AVAILABLE
        risk_ok = no_autonomy and (not (entering_available and unapproved))
        report.add("risk_validation", risk_ok,
                   "describes capability; high-risk capabilities approved" if risk_ok
                   else (f"high-risk capabilities unapproved: {unapproved}" if unapproved
                         else "agent carries an autonomy/execution payload (forbidden)"))

        # governance: entering AVAILABLE requires a policy-governed approval decision
        gov_ok = (not entering_available) or availability_approved
        report.add("governance_validation", gov_ok,
                   "availability policy-approved" if gov_ok
                   else "cannot make agent available without governance approval")
        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise AgentGovernanceError(f"agent governance gate rejected: {names}")
