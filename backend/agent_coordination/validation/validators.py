"""Agent validation — the nine mandated integrity checks (V4-P5).

``AgentValidator`` verifies a registered agent's integrity across the nine mandated
dimensions: identity, lifecycle, capability, assignment, registry, governance,
audit, lineage, and version. It reuses the shared ``ml.validation.ValidationReport``.
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity, validate_assignment_identity
from ..taxonomy import (
    is_category, is_priority, is_capability_risk, is_capability_mode, is_assignment_state,
)
from ..lifecycle import AgentLifecycleState, is_allowed_transition
from ..capabilities import unmet_dependencies
from ..models.domain import AgentRecord, AgentVersion


class AgentValidator:
    """Validates integrity of a registered agent (the nine dimensions)."""

    def validate(self, *, agent: AgentRecord, registry: Any, audit_log: Any,
                 lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()
        aid = agent.agent_id

        # 1. identity integrity
        ident_ok = validate_identity(aid)[0] and is_category(agent.category) \
            and is_priority(agent.priority)
        report.add("identity_integrity", ident_ok, f"agent_id={aid} category={agent.category}")

        # 2. lifecycle integrity — current state is a known state
        report.add("lifecycle_integrity", isinstance(agent.state, AgentLifecycleState),
                   f"state={agent.state.value if isinstance(agent.state, AgentLifecycleState) else agent.state}")

        # 3. capability integrity — modes/risks valid + dependencies declared
        caps_ok = all(is_capability_mode(c.mode) and is_capability_risk(c.risk)
                      for c in agent.capabilities) and not unmet_dependencies(agent)
        report.add("capability_integrity", bool(caps_ok),
                   f"{len(agent.capabilities)} capability(ies)")

        # 4. assignment integrity — every assignment for this agent is well-formed
        try:
            assigns = registry.assignments_for(aid)
            assign_ok = all(validate_assignment_identity(a.assignment_id)[0]
                            and is_assignment_state(a.state) and a.agent_id == aid
                            for a in assigns)
            report.add("assignment_integrity", bool(assign_ok), f"{len(assigns)} assignment(s)")
        except Exception as exc:
            report.add("assignment_integrity", False, f"error: {exc}")

        # 5. registry integrity — registered at this version + lineage
        try:
            rec = registry.get(aid)
            ok = rec.version == agent.version and rec.lineage_id == agent.lineage_id
            report.add("registry_integrity", bool(ok),
                       f"registered version={rec.version} record version={agent.version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        # 6. governance integrity — AVAILABLE agents must be approved
        gov = agent.governance
        gov_ok = (agent.state != AgentLifecycleState.AVAILABLE) or (gov.approval_state == "approved")
        report.add("governance_integrity", bool(gov_ok),
                   f"approval_state={gov.approval_state} state={agent.state.value}")

        # 7. audit integrity — chain verifies + the agent's head is in the log
        try:
            heads = {e.event_hash for e in audit_log.events()}
            ok = audit_log.verify() and (agent.audit_state in heads)
            report.add("audit_integrity", bool(ok), f"chain_verified={audit_log.verify()}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # 8. lineage integrity — the agent's lineage chain verifies
        try:
            chain_ok = bool(agent.lineage_id) and lineage_tracker.verify_chain(agent.lineage_id)
            report.add("lineage_integrity", bool(chain_ok), f"chain_ok={chain_ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # 9. version integrity — recorded version == recomputed content-addressed version
        try:
            expected = AgentVersion.compute(agent.state_signature(), agent.version_previous())
            report.add("version_integrity", agent.version == expected,
                       f"recorded={agent.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        return report

    @staticmethod
    def can_transition(src: AgentLifecycleState, dst: AgentLifecycleState) -> bool:
        return is_allowed_transition(src, dst)
