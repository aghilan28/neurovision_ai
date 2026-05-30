# `backend/agent_coordination/` — Agent Coordination Framework (V4-P5)

> **Layer:** Application (`backend/`) — a V4 subsystem
> **Status:** Implemented (V4-P5)
> **Governing docs:** AP-3/AP-6 (determinism/reproducibility), AP-5/AP-8 (traceability/
> audit), AP-7/NR-8 (boundaries), AP-9/AP-11 (governance), NR-9/NR-10/NR-13; ADR-0013

Introduces **Agents as first-class governed entities** — descriptions of who/what
can perform work (human / system / service / future-AI participants), with declared
**capabilities** and **assignments**. Version 4 answers **"who can perform work?"**.

---

## An Agent is a governed participant — never autonomous authority
An Agent describes capability; it is **not** an autonomous system, a self-modifying
system, or an unbounded executor, and it holds **no autonomous authority**. The
governance gate's *risk* dimension rejects any agent carrying an autonomy/execution
payload, and the service exposes no execute/run API.

## Domain model
`AgentIdentity` (`agent+{hash16}`), `AgentRecord` (the mutable aggregate),
`AgentMetadata`, `AgentCategory` + `AgentPriority` (taxonomy), `AgentCapability`,
`AgentAssignment`, `AgentVersion`, `AgentLifecycleState`, `AgentGovernanceRecord`,
`AgentAuditRecord`, `AgentLineageRecord`, `AgentRegistryRecord`, `AgentRelationship`.

## Hierarchical taxonomy (`taxonomy/`)
A closed, versioned hierarchy with `participant` as the apex, refined by `human`,
`system` → {`service`, `validation`, `analytics`, `knowledge`}, `governance`,
`coordination`. Priorities `low|medium|high|critical`; relation types `supports`,
`depends_on`, `coordinates`, `derived_from`, `influences`.

## Capability system (`capabilities/`)
Each `AgentCapability` declares a **mode** (allowed / restricted / required), a
**risk** level (low / moderate / high / critical), dependencies, and governing
constraint references — **every capability is policy governed**. High/critical-risk
capabilities must be **approved** (`approve_capabilities`) before the agent may
become AVAILABLE. `satisfies(agent, required)` powers capability matching.

## Lifecycle (`lifecycle/`)
`PROPOSED → DRAFT → UNDER_REVIEW → APPROVED → AVAILABLE → {SUSPENDED, RETIRED} →
ARCHIVED` (ARCHIVED terminal; SUSPENDED↔AVAILABLE; UNDER_REVIEW→DRAFT revise).
Forbidden transitions raise `AgentLifecycleError`. APPROVED / AVAILABLE / SUSPENDED /
RETIRED are **policy-governed**; an agent cannot become **AVAILABLE** without
governance approval (and capability approval for high-risk capabilities).

## Assignment system (Task ↔ Agent integration)
`assign(agent, target_id, target_kind, required_capabilities)` requires the agent to
be AVAILABLE and to **satisfy the target's capability requirements** (else
`AgentCapabilityError`). Assignment states: assigned / pending / blocked / revoked /
completed. **An assignment never implies execution** — it is a versioned, lineage-
tracked reference whose node parents the agent + work-unit nodes (so it traces to
the patient via the task).

## Governance, registry, audit, lineage, validation
- **Governance gate** (`governance/`): architecture / quality / context / risk /
  governance — reuses the shared `ml.validation.ValidationReport`.
- **Registry** (`registry/`): no agent exists outside it; silent overwrite forbidden;
  also tracks versioned assignments + relationships.
- **Audit / lineage**: the shared `ImmutableAuditLog` + `ml.lineage.LineageTracker`.
- **Validation** (`validation/`): the nine integrity dimensions — identity,
  lifecycle, capability, assignment, registry, governance, audit, lineage, version.

## Agent ↔ Policy integration
`AgentService(policy_decider=...)` accepts an injected decider. The V4-P2 policy
engine provides `backend.policy_engine.agent_policy_decider` (with
`install_default_agent_policies`), so **every available agent is policy governed**
without `agent_coordination` importing `policy_engine`.

## Quick start
```python
from backend.agent_coordination import (
    AgentService, AgentMetadata, AgentCapability, AgentCategory, AgentLifecycleState,
    CapabilityMode, CapabilityRisk)
asvc = AgentService(lineage_tracker=shared_tracker, policy_decider=agent_decider)
agent = asvc.create_agent(category=AgentCategory.HUMAN, agent_key="dr-reviewer",
    metadata=AgentMetadata(title="Dr Reviewer", role="neurologist"),
    capabilities=(AgentCapability(name="review", mode=CapabilityMode.ALLOWED,
                                  risk=CapabilityRisk.MODERATE),))
for st in (AgentLifecycleState.DRAFT, AgentLifecycleState.UNDER_REVIEW,
           AgentLifecycleState.APPROVED, AgentLifecycleState.AVAILABLE):
    asvc.transition(agent, st)
asn = asvc.assign(agent, target_id=task.task_id, target_kind="task",
                  required_capabilities=["review"], target_lineage_id=task.lineage_id)
assert asvc.validate(agent).ok
```

Run the tests: `pytest tests/test_agent_coordination.py`.
See [`docs/V4_P5_AGENT_COORDINATION.md`](./docs/V4_P5_AGENT_COORDINATION.md).

## Scope guard (NOT built — NR-13)
No self-modifying/autonomous agents, no execution, no autonomous decisions. Agents
describe capability; they hold no autonomous authority.
