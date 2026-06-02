# V2-P7 — Clinical Workstation

> **Layer:** Presentation (`frontend/`) · **Status:** Implemented · **ADR:** [ADR-0006](../../../.gcc/decisions/ADR-0006-v2-p7-p8-workstation-and-certification.md)

The first unified workflow application over all of Version 2. This document
records its architecture, the workflow it presents, and its deterministic state
model.

## 1. Principle
The workstation is a **presentation layer, not a source of truth**. Every value
it shows comes from a *registered artifact*. It imports no domain module (NR-8);
the backend serializes registered artifacts into a snapshot and the workstation
renders that snapshot (stdlib `json` only).

## 2. Architecture diagram (data flow)
```
                       ┌─────────────────────── backend (source of truth) ───────────────────────┐
                       │ CaseService  ReviewService  FindingService  KnowledgeService             │
                       │ MultiCaseIntelligenceService  DecisionSupportService                     │
                       │   registries · immutable audit logs · ONE shared ml.lineage tracker      │
                       └───────────────┬──────────────────────────────────────────────────────────┘
                                       │ scripts.build_workstation_snapshot  (composition point; may import backend)
                                       ▼
                              workstation_snapshot.json   (registered artifacts only; deterministic)
                                       │ stdlib json
                                       ▼
   ┌────────────────────────── frontend.clinical_workstation (imports nothing internal) ──────────┐
   │  state ──▶ navigation ──▶ workspaces ──▶ visualizations                                       │
   │                        └▶ validation (consistency)  ──▶ application.build_workstation_view    │
   │                                                          └▶ reports.render_workstation_html   │
   └───────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 3. Navigation layers
Navigation → Workflow → Visualization → State → Validation → Audit → Reporting.
Ten primary areas (System Status, Cases, Reviews, Findings, Knowledge,
Intelligence, Decision Support, Audit, Lineage, Reports); each `NavArea` carries a
`context` block so moving between areas preserves the current selection.

## 4. Workflow diagram (what the operator traverses)
```
System Status ──▶ Cases ──▶ (case) ──▶ Reviews ──▶ Findings ──▶ Knowledge
      ▲                                                              │
      │                                                              ▼
   Reports ◀── Lineage ◀── Audit ◀── Decision Support ◀── Intelligence
```
Each workspace renders the registered artifacts for its domain (metadata, state,
audit events, lineage, validation, reports) — read-only.

## 5. State diagram (deterministic navigation context)
```
        load(snapshot)                set_context(k=v)            (re-render)
  ∅ ───────────────────▶ default_context ───────────────▶ context' ───────────▶ view
                          (first artifacts)              (records a chosen id; no computation)
```
The tracked keys are `current_patient/case/review/finding/knowledge/intelligence/
decision/audit/lineage`. A transition only records the chosen id — it never
mutates or recomputes an artifact — so state is fully deterministic and the
workstation can create no hidden state.

## 6. Validation (consistency, not recomputation)
`validate_state` runs seven checks: **artifact, registry, version, audit, lineage,
workflow, state** consistency. They confirm the rendered view is coherent and
fully traceable using the validation/audit/lineage facts the backend recorded
(`workflow_consistency` confirms the Patient→…→Decision Support spine verifies and
that every mandated lineage kind — including the parallel Knowledge/Intelligence
branches — exists in the shared lineage graph).

## 7. Scope guard (NOT built — NR-13)
No FHIR/HL7, no EMR/hospital integration, no realtime/streaming EEG, no deployment
infrastructure, no V3/V4 features, and no diagnosis/treatment surfacing. The
workstation only presents what Version 2 already produced and registered.
