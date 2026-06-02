"""Agent capability analysis + matching (V4-P5).

Deterministic, read-only helpers over an agent's declared capabilities. A capability
*describes* what an agent may do — it never executes. These helpers answer questions
the assignment system needs: does an agent satisfy a set of required capabilities?
are a capability's dependencies declared? which high/critical-risk capabilities still
need approval?
"""

from __future__ import annotations

from typing import Sequence

from ..taxonomy import CapabilityRisk, CapabilityMode, CAPABILITY_RISK_RANK


def usable_capabilities(agent) -> tuple[str, ...]:
    """Capability names the agent may use (allowed/required, not restricted)."""
    return tuple(c.name for c in agent.capabilities if c.mode != CapabilityMode.RESTRICTED)


def satisfies(agent, required: Sequence[str]) -> tuple[bool, list]:
    """Whether the agent provides every required capability (usable). Returns (ok, missing)."""
    usable = set(usable_capabilities(agent))
    missing = [r for r in required if r not in usable]
    return (len(missing) == 0), missing


def unmet_dependencies(agent) -> list:
    """Capability dependencies that are not themselves declared on the agent."""
    declared = set(agent.capability_names)
    unmet = []
    for c in agent.capabilities:
        for dep in c.depends_on:
            if dep not in declared:
                unmet.append({"capability": c.name, "missing_dependency": dep})
    return unmet


def high_risk_unapproved(agent) -> list:
    """High/critical-risk capabilities that governance has not yet approved."""
    threshold = CAPABILITY_RISK_RANK[CapabilityRisk.HIGH]
    return [c.name for c in agent.capabilities
            if CAPABILITY_RISK_RANK.get(c.risk, 0) >= threshold and not c.approved]


def requires_capability_approval(agent) -> bool:
    """True if the agent declares any high/critical-risk capability (needs approval)."""
    threshold = CAPABILITY_RISK_RANK[CapabilityRisk.HIGH]
    return any(CAPABILITY_RISK_RANK.get(c.risk, 0) >= threshold for c in agent.capabilities)


def capability_summary(agent) -> dict:
    by_mode: dict = {}
    by_risk: dict = {}
    for c in agent.capabilities:
        by_mode[c.mode] = by_mode.get(c.mode, 0) + 1
        by_risk[c.risk] = by_risk.get(c.risk, 0) + 1
    return {"n_capabilities": len(agent.capabilities), "by_mode": dict(sorted(by_mode.items())),
            "by_risk": dict(sorted(by_risk.items())),
            "unmet_dependencies": unmet_dependencies(agent),
            "high_risk_unapproved": high_risk_unapproved(agent)}
