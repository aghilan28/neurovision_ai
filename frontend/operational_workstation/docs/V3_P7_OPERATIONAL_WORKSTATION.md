# V3-P7 — Operational Intelligence Workstation (design notes)

> **Phase:** V3-P7 · **Subsystem:** `frontend/operational_workstation/` · **ADR:** ADR-0010

## Purpose
Turn six independent V3 subsystems into **one unified operational environment**. The
workstation **exposes** the operational system (visibility, monitoring,
investigation, intelligence, recommendations); it **creates no operational logic**.

## The seam (NR-8)
`frontend/` imports no domain module. The only seam is
`scripts/build_operational_workstation_snapshot.py`, which composes the real V3
services over **one shared lineage tracker**, drives a small deterministic
multi-case workflow, and serializes every registered artifact (registries, reports,
immutable audit logs, the lineage graph, validation results) into a single
deterministic JSON snapshot (`sort_keys=True`, no wall-clock). The workstation reads
that snapshot with stdlib `json` only.

## Application architecture
- **Navigation layer** (`navigation/`) — ten primary areas; each carries the
  preserved deterministic context block.
- **Workspace layer** (`workspaces/`) — one workspace per area; each `*_pages(state)`
  builds `Page` view-models (sections + visualizations) from registered artifacts.
- **Visualization layer** (`visualizations/`) — ten chart families as plain
  JSON-able specs (no recomputation).
- **State layer** (`state/`) — loads the snapshot; tracks `current_*` navigation
  context; every transition is deterministic (records the chosen id only).
- **Validation layer** (`validation/`) — six presentation-consistency checks.
- **Reporting layer** (`reports/`) — the report center + a deterministic static
  offline HTML renderer (inline CSS + inline SVG, CSS-only tabs, no JavaScript).

## Primary areas + workspaces
| Area | Displays |
|------|----------|
| System Health | system/operational health + risk headline, subsystem status board, counts |
| Events | event registry, taxonomy, relationships, audit, lineage, validation |
| Timelines | timelines, histories, evolution, temporal analytics (logical steps) |
| Workflows | registry, transitions, dependencies, bottlenecks, efficiency (per workflow) |
| Graph | node/edge/relationship registry, projections, structure |
| Analytics | metrics, health, performance, quality, trends, risk |
| Recommendations | guidance, priorities, optimization suggestions, escalation candidates |
| Audit | unified browser over every V3 immutable audit log + event/version history |
| Lineage | the Patient→…→Recommendation traceability chain + dependency profile |
| Reports | every registered report across the six subsystems |

## State management
`CONTEXT_KEYS` = current event / timeline / workflow / graph / analytics /
recommendation / audit / lineage. `default_context()` seeds deterministically from
the first available artifacts; `set_context()` validates the key and records the id;
nothing is computed or mutated.

## Validation (six consistency dimensions)
`registry_consistency` (displayed collections match registry counts),
`audit_consistency` (every subsystem audit log verifies), `lineage_consistency`
(per-artifact + end-to-end chain verifies), `visualization_consistency` (every chart
spec resolves to registered data — no dangling graph edges, matched bar
labels/values, required keys), `report_consistency` (every subsystem exposes its
registered reports), `state_consistency` (navigation context references existing
artifacts).

## Traceability
The Lineage workspace renders the mandated ordering Patient → Case → Review →
Finding → Knowledge → Decision → Event → Timeline → Workflow → Graph → Analytics →
Recommendations, proven by the representative chain whose anchor is a real
recommendation (`verify_chain` true to the patient).

## Determinism (NR-9/NR-10)
The snapshot is byte-deterministic; the view-model and HTML are pure functions of
the snapshot. Same inputs → identical snapshot, view, and HTML.

## Scope guard (NR-13)
No realtime intelligence, autonomous agents, multi-site federation, distributed
intelligence, streaming EEG, FHIR/HL7/EMR, or V4 features. No clinical
recommendations/diagnosis/treatment. Presentation only — no source of truth, no
engine.
