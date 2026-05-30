# ADR-0004 — V2-P3 Findings & Interpretation Layer + V2-P4 Clinical Knowledge Layer

> **Type:** Decision Record (Governance & Context Control)
> **Status:** Accepted
> **Phase:** V2-P3 + V2-P4
> **Builds on:** ADR-0001, ADR-0002, [ADR-0003](./ADR-0003-v2-p1-p2-clinical-case-and-review.md)
> **Enforces / honors:** AP-1 (vertical population, no re-layering), AP-4/NR-4
> (evidence/uncertainty preserved), AP-5/AP-8/NR-11 (traceability/audit), AP-6/NR-10
> (reproducibility), AP-7/NR-8 (boundaries), AP-9/NR-5 (this record), NR-6 (reuse),
> NR-13 (scope)
> **Decision owner:** Application/platform engineering (Kiro-assisted, subject to NR-7)

Captures why the V2-P3 Findings & Interpretation Layer and V2-P4 Clinical Knowledge
Layer are shaped as they are, so the rationale survives turnover (NR-14).

---

## 1. Context

The platform had Cases/Studies/Reviews (V2-P1/P2) over V1 intelligence outputs, but
lacked **clinical meaning**: findings, interpretation, and knowledge context. V2-P3
introduces the **Finding** (a structured observation linked to evidence) and the
**Interpretation** (separate); V2-P4 introduces a structured **Knowledge** base
(terminology/concepts/taxonomy/ontology/relationships). Decision support and
diagnosis engines remain **forbidden** (V2-P6+ / never).

## 2. Decisions

### D1 — Own identity authorities; ``clinical_cases`` left untouched
The V2-P1 ``clinical_cases.identity`` reserves ``finding``/``decision`` as future-
blocked patient-graph markers, and a passing test asserts this. To honour "do not
redesign previous phases," V2-P3 mints findings/evidence/interpretation through its
**own** authority (``clinical_findings.identity``) and V2-P4 mints knowledge ids
through its **own** authority (``clinical_knowledge.identity``). Both emit the same
``"{kind}+{hash16}"`` *format*, so the existing case-system validator interoperates,
but ``clinical_cases`` is unchanged and its tests stay green. ``decision`` remains
blocked everywhere (V2-P6).

### D2 — A finding never exists without evidence
``create_finding`` requires ≥ 1 evidence spec and ``FindingRegistry.register``
rejects an evidence-less record. Evidence links reference **registered** V1/V2
artifacts; ``evidence_confidence`` is a *recorded* value, never computed — the
findings layer introduces no hidden clinical assumption (the directive's explicit
prohibition).

### D3 — Interpretation is a separate entity (never merged)
``FindingInterpretation`` has its own id/version/lineage/audit trail. The finding
stores interpretation *ids* only; the finding's ``to_dict`` contains no
interpretation text. An interpretation's supporting evidence must be a subset of the
finding's evidence (validated).

### D4 — One shared lineage graph across V1 + V2-P1..P4
All services share a single ``ml.lineage.LineageTracker``. Evidence nodes parent the
inference node; findings parent the review + evidence nodes; interpretations parent
the finding; **relationship** nodes parent *both* endpoints. Thus a single
``verify_chain`` from a ``finding_describes_concept`` relationship spans Patient →
Case → Study → Review → Inference → Evidence → Finding → Interpretation → Concept →
Term — the deliverable's complete traceability — and V1/V2-P1/P2 lineage is reused,
never disturbed.

### D5 — Knowledge is data, not logic; practical ontology
The default knowledge base is a **declarative seed** loaded through governed,
audited, versioned methods (NR: "knowledge must never be hidden in code"). The
ontology is **practical** (entity kinds + relationship schema + executable
constraints), not an OWL reasoner ("do not overengineer"). The layer models
terminology/concepts/relationships and performs **no diagnosis or decision support**.

### D6 — One immutable audit primitive, reused everywhere
The tamper-evident hash-chained ``ImmutableAuditLog`` (from ``clinical_cases.audit``)
is reused by findings (``FindingAuditRecord``) and knowledge
(``KnowledgeAuditRecord``) — one verified implementation (NR-6).

### D7 — Versions are per-entity hash chains; registries reject silent overwrite
Consistent with ADR-0003 D4/D6: finding versions and the knowledge-base version
chain ``hash(state, previous)`` (unique per mutation); registries reject re-
registering the same version with different content.

### D8 — Tests live in top-level ``tests/`` (consistent with ADR-0001 D4).

## 3. Consequences

- Required deliverable executes with complete traceability (``scripts/
  run_clinical_knowledge_workflow.py``; ``scripts/verify_v2_p3_p4.py`` → all 19
  criteria).
- Acyclic DAG preserved: the new subsystems import ``ml`` + intra-``backend`` only,
  never ``frontend`` (enforced by ``tests/test_boundaries.py``).
- V1 and V2-P1/P2 remain intact (their nodes are referenced, never mutated). 190
  tests pass; verify_v1 / verify_v2 / verify_v2_p3_p4 all green.

## 4. Scope guard (explicitly NOT built — NR-13)

Decision support, diagnosis engines, treatment recommendations, clinical deployment,
FHIR/HL7, EMR integration, real-time systems, and any V3/V4 feature. The
``decision`` identity kind stays blocked. Forward seams (finding→decision links,
escalation hooks) remain inert.

## 5. Follow-ups / recorded debt (NR-2)

- Decision layer (V2-P6) attaches at the reserved ``decision`` identity + the
  finding's forward links — by extension, never re-layering (AP-1).
- The clinical subsystems persist in-memory; durable, checksummed on-disk
  persistence (the V1 artifact-store pattern) remains the natural next increment.
