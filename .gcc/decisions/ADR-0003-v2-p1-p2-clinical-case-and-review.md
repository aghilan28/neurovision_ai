# ADR-0003 — V2-P1 Clinical Case Foundation + V2-P2 Clinical Review Workflow

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** V2-P1 + V2-P2
> **Builds on:** [ADR-0001](./ADR-0001-v1-p5-p6-baseline-models-and-uncertainty.md), [ADR-0002](./ADR-0002-v1-p7-p8-offline-inference-and-research-app.md)
> **Enforces / honors:** AP-1 (vertical population, no re-layering), AP-5/AP-8/NR-11
> (traceability/audit), AP-6/NR-10 (reproducibility), AP-7/NR-8 (boundaries), AP-9/NR-5
> (this record), NR-6 (reuse, don't re-implement), NR-13 (scope)
> **Decision owner:** Application/platform engineering (Kiro-assisted, subject to NR-7)

Captures why the V2-P1 Clinical Case Foundation and V2-P2 Clinical Review Workflow
are shaped as they are, so the rationale survives turnover (NR-14).

---

## 1. Context

Version 2's purpose is **clinical workflow modeling** — not deployment, FHIR, EMR,
real-time, or production infrastructure. V1 revolved around files/models/inference;
V2 must revolve around Patients, Cases, Studies, Reviews. V2-P1 introduces the
**Case** as the first-class organizational object; V2-P2 introduces structured
**Review**. Both are built in the `backend` Application layer on top of the certified
V1 platform.

**Reconciliation with the V1→V2 readiness gate.** The V1 certification
(`docs/certification/v1/V2_READINESS_GATE.md`) records that *clinical deployment/use*
is NOT granted until the real-EEG and governance-mechanization blockers (B1–B4)
close. V2-P1/P2 here is **clinical workflow *modeling* on the existing synthetic,
deterministic pipeline** — a domain/architecture exercise that introduces no
clinical-deployment, real-time, or hospital-integration capability. It therefore
does not breach the gate: the blockers still gate *clinical use*, which remains
explicitly out of scope (NR-13). This distinction is recorded here per NR-5.

## 2. Decisions

### D1 — Cases/Reviews live in `backend/`, composing V1 (not re-implementing it)
`backend/clinical_cases` and `backend/clinical_review` are Application-layer
subsystems. They **reuse** the V1 primitives — `ml.provenance` (content ids),
`ml.lineage` (`LineageTracker`/`make_lineage_record`), `ml.validation`
(`ValidationReport`) — and **integrate** with `backend.offline_inference`
registered artifacts. No DSP/model/metric/lineage logic is re-implemented (NR-6).
The seven-layer architecture is **populated, not re-layered** (AP-1).

### D2 — Content-addressed clinical identities; never filename/folder-derived
Patient/Case/Study/Review ids are deterministic content hashes of deidentified
component keys (`"{kind}+{hash16}"`), with non-root ids embedding their parent
(`derived_from`). This satisfies "Cases must never depend on filenames/folders" and
"survive future architecture evolution." `finding`/`decision` identity policies
exist (so the system can *describe* them) but are **blocked** from minting — the
Findings/Decisions layers are forbidden until a later version (NR-13).

### D3 — One shared lineage graph across V1 + V2
The Case and Review services share a single `ml.lineage.LineageTracker`, and
attaching a V1 inference **imports the V1 lineage nodes** into it. A single
`verify_chain` from the review head therefore proves end-to-end traceability:
Review → Session → Case → Study → Inference → Uncertainty → Evaluation → Training.
This realizes the directive's required deliverable and keeps V1 lineage intact.

### D4 — Versions are per-entity hash chains, not bare state hashes
A `CaseVersion`/`ReviewVersion` chains `hash(state_signature, previous_version)`.
Using the state signature alone caused a real defect (a reopen returns to a
logically identical state, reproducing an earlier version string while metadata
advanced — tripping the registry's overwrite guard). Chaining guarantees a unique,
monotonic version per mutation while keeping reproducibility (identical input
sequences yield identical version chains). The defect was caught by a test and
fixed before completion (NR-2: no hidden debt).

### D5 — One immutable audit primitive, parameterized by record type
The tamper-evident, hash-chained `ImmutableAuditLog` is implemented once in
`clinical_cases.audit` and reused by `clinical_review` (bound to
`ReviewAuditRecord`). Two audit subsystems exist (per the directive's structure) but
share one verified implementation (NR-6).

### D6 — Registries reject silent overwrite; nothing exists outside a registry
Case and Review registries key on `(id, version)` and reject re-registering the
same version with different content. A new version is an *update* (the audit log +
version chain record the change), not a silent overwrite.

### D7 — Tests live in top-level `tests/`
Consistent with ADR-0001 D4: the directive's per-subsystem `tests/` requirement is
satisfied by subject-matter test files under the authoritative cross-cutting
`tests/` root (identity, lifecycle, audit, registry, lineage, validation, reports,
sessions, assignment, tracking, e2e, boundaries).

## 3. Consequences

- The required deliverable executes with complete traceability: Patient → Case →
  Study → Inference Artifacts → Review Session → Review Lifecycle → Audit Trail →
  Lineage Trail (`scripts/run_clinical_workflow.py`; `scripts/verify_v2.py`).
- The acyclic DAG is preserved: clinical subsystems import `ml` + intra-`backend`
  only and never `frontend` (enforced by `tests/test_boundaries.py`).
- V1 remains intact (its inference runs still validate; its lineage nodes are
  referenced, never mutated). 155 tests pass; verify_v1 and verify_v2 both green.

## 4. Scope guard (explicitly NOT built — NR-13)

FHIR, HL7, hospital/EMR integration, real-time/streaming, clinical deployment,
decision support, the Knowledge layer, and the Findings/Decisions layers are **out
of V2-P1/P2 scope** and were not implemented. Forward seams (future identity
policies, the assignment escalation hook, review→finding/decision links) are inert
placeholders only.

## 5. Follow-ups / recorded debt (NR-2)

- Findings/Decisions layers (future) attach at the reserved identity policies and
  the review's forward links — by extension, never re-layering (AP-1).
- The clinical subsystems persist in-memory today; durable, checksummed on-disk
  persistence of case/review registries + audit logs is a natural next increment
  (the artifact-store pattern from V1 applies directly).
- Real-EEG ingestion and the V1 certification gaps (ADR-0002 G1–G4) remain the
  prerequisites for any clinical-deployment ambitions (out of V2 scope).
