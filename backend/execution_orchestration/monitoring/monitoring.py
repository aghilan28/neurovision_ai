"""Execution monitoring (V4-P6).

**Monitoring observes execution; it never modifies it.** These helpers derive a
read-only :class:`ExecutionStatus` snapshot from an execution's lifecycle state — a
deterministic [0,1] progress index (from the state, never wall-clock), plus observed
blocking conditions, risks, escalations, and the outcome. The service stamps the
snapshot onto the execution as a *projection*; monitoring itself returns pure data.
"""

from __future__ import annotations

from ..lifecycle import ExecutionLifecycleState as S
from ..models.domain import ExecutionStatus

# deterministic progress index per lifecycle state (state-derived, not time-derived).
_PROGRESS: dict[str, float] = {
    S.PROPOSED.value: 0.0, S.QUEUED.value: 0.1, S.AUTHORIZED.value: 0.25,
    S.ACTIVE.value: 0.5, S.PAUSED.value: 0.5, S.BLOCKED.value: 0.4,
    S.COMPLETED.value: 1.0, S.TERMINATED.value: 1.0, S.ARCHIVED.value: 1.0,
}

# the terminal outcome per state (observed, not enacted).
_OUTCOME: dict[str, str] = {
    S.COMPLETED.value: "completed", S.TERMINATED.value: "terminated",
    S.ARCHIVED.value: "archived",
}


def observe(execution) -> ExecutionStatus:
    """Return a read-only status snapshot for the execution's current state."""
    state = execution.state.value
    blocking: list[str] = []
    risks: list[str] = []
    escalations: list[str] = []
    if state == S.BLOCKED.value:
        blocking.append("execution_blocked")
    if state == S.PAUSED.value:
        risks.append("execution_paused")
    if execution.governance.escalation_required:
        escalations.append("governance_escalation_required")
    if execution.governance.authorization_state == "escalated":
        escalations.append("authorization_escalated")
    return ExecutionStatus(
        state=state, progress=_PROGRESS.get(state, 0.0),
        blocking_conditions=tuple(blocking), risks=tuple(risks),
        escalations=tuple(escalations), outcome=_OUTCOME.get(state, ""))


def monitoring_summary(executions) -> dict:
    by_state: dict = {}
    blocked = 0
    escalated = 0
    for e in executions:
        by_state[e.state.value] = by_state.get(e.state.value, 0) + 1
        st = observe(e)
        if st.blocking_conditions:
            blocked += 1
        if st.escalations:
            escalated += 1
    return {"n_executions": len(list(executions)), "by_state": dict(sorted(by_state.items())),
            "n_blocked": blocked, "n_escalated": escalated}
