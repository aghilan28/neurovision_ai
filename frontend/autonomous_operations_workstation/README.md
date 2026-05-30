# `frontend/autonomous_operations_workstation` — Autonomous Operations Workstation (V4-P8)

The first unified **human-oversight** environment — the operational command center
over every Version 4 subsystem (Goals, Policies, Plans, Tasks, Agents, Executions),
the V4-P7 Governance Intelligence Layer, and unified Audit, Lineage, Reports, and a
System Health landing area.

## Humans stay in control

The workstation is **observation, investigation, authorization, intervention, and
escalation** — never execution / planning / agent / governance logic. Humans remain
in control, accountable, and capable of intervention.

## Presentation layer, not a source of truth (NR-8)

Everything displayed originates from **registered artifacts** — registries, reports,
immutable audit logs, the lineage graph, recorded validation, and the governance
intelligence — serialized into a JSON snapshot by
`scripts.build_autonomous_operations_workstation_snapshot`. The workstation reads the
snapshot with stdlib `json` only and imports **no** domain module. The only state it
tracks is deterministic navigation context.

## Navigation (11 primary areas)

System Health · Goals · Policies · Plans · Tasks · Agents · Executions · Governance ·
Audit · Lineage · Reports.

## Intervention controls (governed, never performed here)

`suspend_agent`, `pause_execution`, `terminate_execution`, `escalate_approval`,
`request_review`. Each control is a *description* of a governed backend action and
declares: it **requires authorization** and **generates audit + lineage + governance
records**. No hidden actions — every control is explicit and fully attributed; the
backend performs the action, the workstation only surfaces and authorizes it.

## Structure

| Path | Responsibility |
|------|----------------|
| `schemas/` | view-model contracts (`Section`, `Visualization`, `InterventionControl`, `Page`, `NavArea`, `WorkstationView`, `ValidationReport`) |
| `components/` | presentation helpers + the shared entity-workspace builder |
| `state/` | load the snapshot + deterministic navigation context |
| `navigation/` | assemble the 11 primary nav areas |
| `goals/ policies/ plans/ tasks/ agents/ executions/` | the per-entity workspaces |
| `governance/` | the governance-intelligence workspace (approvals/violations/escalations/risk/health) |
| `audit/` | unified audit browser |
| `lineage/` | end-to-end lineage explorer |
| `reports/` | report center |
| `system_health/` | the landing / overview area |
| `controls/` | governed intervention controls |
| `validation/` | the six presentation-integrity consistency checks |
| `application/` | the composition root (`build_workstation_view`) |

## Validation

`validate_state(state)` runs six consistency checks: registry, audit, lineage,
visualization, report, and state consistency — confirming the displayed view is
coherent, fully traceable (the Patient → … → Governance Intelligence spine), and
fully registered.
