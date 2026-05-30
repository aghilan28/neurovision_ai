# V3 Audit Framework

> **Document type:** Certification (V3) · **Status:** Authoritative
> **Realizes:** AP-8 (auditability), AP-11 (mechanized governance), NR-12
> **Companion:** `V3_CERTIFICATION_STANDARD.md`, `V3_READINESS_ASSESSMENT.md`

Defines **how** the V3 audit is conducted: the audit categories, the procedure and
checklist per category, the evidence each requires, and the escalation rules when a
check fails. Every check is **objective** (a passing test, a reproducible script, or
a registered artifact).

---

## 1. Audit categories

| # | Category | Scope |
|---|----------|-------|
| A1 | Event Audit | `backend/operational_events` — events first-class, immutable, observed, governed. |
| A2 | Timeline Audit | `backend/temporal_intelligence` — timelines/histories/evolution/analytics derived from events. |
| A3 | Workflow Audit | `backend/workflow_intelligence` — workflows derived; transitions/deps/bottlenecks/efficiency. |
| A4 | Graph Audit | `backend/operational_graph` — derived graph, closed ontology, no graph-only truth, query layer. |
| A5 | Analytics Audit | `backend/operational_analytics` — derived intelligence; never a source of truth. |
| A6 | Recommendation Audit | `backend/operational_recommendations` — explainable, evidence+analytics-linked; suggestions only. |
| A7 | Workstation Audit | `frontend/operational_workstation` — import-pure presentation; six consistency checks. |
| A8 | Governance Audit | versioning, lineage, ADRs, scope discipline. |
| A9 | Quality Audit | determinism, reproducibility, tests, ruff. |
| A10 | Context Audit | end-to-end traceability Patient → … → Recommendation. |

## 2. Audit procedure (per category)

1. **Locate evidence** — the registry/report/audit/lineage artifact + the test(s)
   and verification-script criterion that exercise it.
2. **Run the check** — execute the test/script; read the registered artifact.
3. **Record the result** — PASS/FAIL with the command and the observed value.
4. **Escalate on FAIL** — apply the escalation rule (§4); do not certify around it.

## 3. Audit checklists + evidence requirements

### A1 Event Audit
- [ ] Events immutable + superseded-never-rewritten; taxonomy closed.
- [ ] Event audit log `verify()`s true; every event lineage `verify_chain`s true.
- *Evidence:* `tests/test_operational_events.py`, `verify_v3_p1_p2` (criteria 1–10),
  event registry + audit blocks in the snapshot.

### A2 Timeline Audit
- [ ] Timelines/histories/evolution/analytics derived strictly from events; durations in logical steps.
- *Evidence:* `tests/test_temporal_intelligence.py`, `verify_v3_p1_p2` (11–20), temporal blocks.

### A3 Workflow Audit
- [ ] Workflows derived from events/temporal (no hidden state); transitions/deps/bottlenecks/efficiency present.
- *Evidence:* `tests/test_workflow_intelligence.py`, `verify_v3_p3_p4`, workflow blocks.

### A4 Graph Audit
- [ ] Every node has a real `source_id`; every edge ontology-validated + `derived_from`; query layer read-only.
- *Evidence:* `tests/test_operational_graph.py`, `verify_v3_p3_p4`, graph registry + projection.

### A5 Analytics Audit
- [ ] Six engines produce bounded, explainable metrics; gate's risk dimension forbids non-derived analytics.
- *Evidence:* `tests/test_operational_analytics.py`, `verify_v3_p5_p6` (1–9), analytics blocks.

### A6 Recommendation Audit
- [ ] Every recommendation evidence-linked + analytics-linked; suggestions only; escalation is candidate-only.
- *Evidence:* `tests/test_operational_recommendations.py`, `verify_v3_p5_p6` (10–17), recommendation blocks.

### A7 Workstation Audit
- [ ] Ten areas render; six consistency checks pass; imports no domain module; deterministic HTML.
- *Evidence:* `tests/test_operational_workstation.py`, `tests/test_boundaries.py`, `verify_v3_p7_p8` (1–12).

### A8 Governance Audit
- [ ] ADR-0007…0010 accepted; one shared lineage tracker + shared audit log (no parallel systems).
- *Evidence:* `.gcc/decisions/`, shared-tracker assertions in the e2e tests.

### A9 Quality Audit
- [ ] Full suite green; snapshot + artifacts reproducible; `ruff` clean on new code.
- *Evidence:* `python -m pytest` (363 passed), determinism tests, `ruff check`.

### A10 Context Audit
- [ ] `verify_chain` from a recommendation reaches the patient through every layer.
- *Evidence:* `tests/test_v3_p5_p6_e2e.py`, snapshot `representative_chain.verified`, `verify_v3_p7_p8` (20).

## 4. Audit escalation rules

| Severity | Trigger | Action |
|----------|---------|--------|
| **Blocking** | A delivered-scope exit criterion FAILs, a boundary violation, or any audit chain fails to verify. | Stop. NOT CERTIFIED until fixed + re-run. |
| **Major** | A dimension scores < 75 for delivered scope, or a registered artifact is missing. | Record in Gap Analysis with remediation; may block depending on dimension. |
| **Minor / Provisional** | An *inherited* foundational dependency (synthetic data, unmechanized governance, in-memory persistence) limits a claim. | Record in Gap Analysis + Risk Review; allows CERTIFIED (QUALIFIED). |

## 5. Auditor's note

The auditor must **re-run** the evidence, not trust prior runs. A green history is
not a substitute for a green run on the audited commit.
