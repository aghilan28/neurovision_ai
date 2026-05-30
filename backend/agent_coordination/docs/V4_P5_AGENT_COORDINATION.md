# V4-P5 — Agent Coordination Framework (design notes)

> **Phase:** V4-P5 · **Subsystem:** `backend/agent_coordination/` · **ADR:** ADR-0013

## Purpose
Make **agents** first-class governed participants: who/what can perform work, with
declared capabilities and assignments. Versioned, traceable, auditable, lineage-
tracked, governed, deterministic, recoverable — and holding **no autonomous
authority**.

## Why "describes capability, not authority"
The directive forbids autonomous/self-modifying/unbounded executors. An Agent
carries metadata (title, role, contact), declared capabilities, and governance — but
no executable payload. Enforced structurally: the governance gate's *risk* dimension
fails an agent whose tags include an autonomy/execution marker, and the service has
no execute/run method.

## Identity
`agent+{hash16}` derived from `(category, agent_key)` — the *definition*, not the
lifecycle state. Assignments use `agentassign+{hash16}`; relationships use
`agentrel+{hash16}`.

## Capability governance
Capabilities declare mode (allowed/restricted/required) and risk
(low/moderate/high/critical). High/critical-risk capabilities are unusable for
AVAILABLE until `approve_capabilities` records governance approval — enforced in the
gate's *risk* dimension (`high_risk_unapproved`). Capability dependencies must be
declared on the same agent (`unmet_dependencies`).

## Lifecycle + governance
The eight-state machine adds AVAILABLE as the operational gate (SUSPENDED↔AVAILABLE).
Four transitions are **policy-governed** (hooks agent_approval / agent_availability /
agent_suspension / agent_retirement). The service consults the injected
`policy_decider`; a denial raises `AgentGovernanceError`, blocking the move. An agent
cannot reach **AVAILABLE** without approval.

## Assignments (Task ↔ Agent)
`assign` requires the agent AVAILABLE and `satisfies(agent, required_capabilities)`;
otherwise `AgentCapabilityError`. An assignment is a versioned reference (state
assigned/pending/blocked/revoked/completed) and **never implies execution**. Its
lineage node parents the agent node + the work-unit (task) node, so
`verify_chain(assignment)` spans `Patient → … → Task → Agent assignment`.

## Determinism (NR-9/NR-10)
No wall-clock. Identities, versions (`hash(state_signature, previous)`), and audit
heads are content-addressed, so identical inputs reproduce identical agents.

## Validation (nine dimensions)
identity · lifecycle · capability · assignment · registry · governance · audit ·
lineage · version — all via the shared `ml.validation.ValidationReport`.

## Scope guard (NR-13)
No self-modifying/autonomous agents, execution, autonomous decisions, or V5 features.
