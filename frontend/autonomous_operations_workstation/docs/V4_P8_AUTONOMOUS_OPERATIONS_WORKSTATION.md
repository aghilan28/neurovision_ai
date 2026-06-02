# V4-P8 — Autonomous Operations Workstation

## Objective

Create the first **human-oversight** environment: the operational command center.
Humans remain in control, accountable, and capable of intervention. The workstation
is observation / investigation / authorization / intervention / escalation — **not**
execution, planning, agent, or governance logic.

## Boundary (NR-8)

The workstation imports **no** domain module. Its only contract with the backend is
the JSON **snapshot** built by
`scripts.build_autonomous_operations_workstation_snapshot`, which composes the real
Version 4 services (V4-P1…P6) + the V4-P7 Governance Intelligence Layer over one
shared lineage tracker and serializes every registered artifact. The workstation
reads the snapshot with stdlib `json`.

## Workspaces (eleven primary areas)

System Health · Goals · Policies · Plans · Tasks · Agents · Executions · Governance ·
Audit · Lineage · Reports. Each per-entity workspace shows the registry, lifecycle
state distribution, governance state, audit integrity, lineage integrity, and the
registered reports. The Governance workspace presents the V4-P7 approval / violation /
escalation / risk analytics and the governance health score. The Audit browser is a
unified view over every immutable audit log; the Lineage explorer shows the
Patient → … → Governance Intelligence spine and traceability graph; the Report center
lists every registered report.

## Intervention controls

Governed, presentation-only descriptions of backend actions: `suspend_agent`,
`pause_execution`, `terminate_execution`, `escalate_approval`, `request_review`. Each
declares `requires_authorization=True` and `generates_audit / generates_lineage /
generates_governance_record = True`. No hidden actions: the backend performs the
action; the workstation surfaces and authorizes it.

## State management

Deterministic navigation context (current goal / policy / plan / task / agent /
execution / governance / audit / lineage). Setting a context only records a chosen
id — nothing is computed or mutated.

## Validation

Six presentation-integrity consistency checks: registry, audit, lineage,
visualization, report, and state consistency.

## Integration

Integrates (via the snapshot) with Version 4 Goals/Policies/Plans/Tasks/Agents/
Executions, the V4-P7 Governance Intelligence Layer, and (transitively) Version 3
analytics/recommendations and Version 0 governance/quality/context systems. No
isolated implementation.

## Out of scope (forbidden work)

No simulation / scenario / forecasting engine, no self-modifying agents, no autonomous
goal creation, no autonomous policy updates, no Version 5 features.
