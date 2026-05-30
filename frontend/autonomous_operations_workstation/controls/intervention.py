"""Intervention controls (V4-P8) — governed human-oversight actions (presentation).

The workstation is the human-oversight command center: observation, investigation,
authorization, intervention, escalation. It is **not** execution/governance logic —
so an intervention control is a *description* of a governed backend action, not the
action itself. Each control declares the authorization it requires and the records
the backend will generate (audit + lineage + governance). Nothing happens here; the
control is the explicit, fully-attributed request a human authorizes. **No hidden
actions** — every control is surfaced.

Controls (per the directive): suspend agent, suspend execution, escalate approval,
request review, pause execution, terminate execution.
"""

from __future__ import annotations

from ..schemas import InterventionControl

# the live agent state from which an agent may be suspended.
_AGENT_SUSPENDABLE = {"available"}
# execution states from which pause/terminate are meaningful.
_EXEC_ACTIVE = {"active", "queued", "authorized", "paused", "blocked"}
_EXEC_TERMINAL = {"completed", "terminated", "archived"}


def controls_for_agent(agent: dict) -> list:
    """Governed controls available for one agent (suspend)."""
    state = agent.get("state", "")
    aid = agent.get("id", "")
    enabled = state in _AGENT_SUSPENDABLE
    return [InterventionControl(
        action="suspend_agent", target_kind="agent", target_id=aid, enabled=enabled,
        rationale=("agent is available and may be suspended" if enabled
                   else f"agent state={state} is not suspendable"))]


def controls_for_execution(execution: dict) -> list:
    """Governed controls available for one execution (pause / terminate / escalate / review)."""
    state = execution.get("state", "")
    eid = execution.get("id", "")
    active = state in _EXEC_ACTIVE and state not in _EXEC_TERMINAL
    return [
        InterventionControl(action="pause_execution", target_kind="execution", target_id=eid,
                            enabled=active,
                            rationale="execution is in-flight and may be paused" if active
                            else f"execution state={state} cannot be paused"),
        InterventionControl(action="terminate_execution", target_kind="execution", target_id=eid,
                            enabled=active,
                            rationale="execution is in-flight and may be terminated" if active
                            else f"execution state={state} cannot be terminated"),
        InterventionControl(action="escalate_approval", target_kind="execution", target_id=eid,
                            enabled=True,
                            rationale="authorization may be escalated for human decision"),
        InterventionControl(action="request_review", target_kind="execution", target_id=eid,
                            enabled=True, rationale="a human review may be requested"),
    ]


def build_controls(state) -> list:
    """Every governed intervention control derivable from the snapshot (agents + executions)."""
    controls: list = []
    for agent in state.records("agents"):
        controls.extend(controls_for_agent(agent))
    for execution in state.records("executions"):
        controls.extend(controls_for_execution(execution))
    return controls


def controls_summary(controls: list) -> dict:
    by_action: dict = {}
    enabled = 0
    for c in controls:
        cd = c.to_dict() if isinstance(c, InterventionControl) else c
        by_action[cd["action"]] = by_action.get(cd["action"], 0) + 1
        if cd.get("enabled"):
            enabled += 1
    # the invariant every control must satisfy (governed + audited + attributed).
    governed = all(
        (c.to_dict() if isinstance(c, InterventionControl) else c)["requires_authorization"]
        and (c.to_dict() if isinstance(c, InterventionControl) else c)["generates_audit"]
        and (c.to_dict() if isinstance(c, InterventionControl) else c)["generates_lineage"]
        and (c.to_dict() if isinstance(c, InterventionControl) else c)["generates_governance_record"]
        for c in controls)
    return {"n_controls": len(controls), "n_enabled": enabled,
            "by_action": dict(sorted(by_action.items())), "all_governed": governed}
