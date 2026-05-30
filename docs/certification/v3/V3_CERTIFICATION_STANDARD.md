# V3 Certification Standard

> **Document type:** Certification (V3) · **Status:** Authoritative for V3 audit
> **Owner:** Governance & Context Control (GCC) · **Realizes:** AP-8 (auditability), AP-9 (versioned governance), AP-11 (mechanized governance), NR-12 (version gate)
> **Companion docs:** the other files in `docs/certification/v3/`

This standard defines **what it means for Version 3 to be certified** and the
**evidence** required. Certification is **earned, not assumed** (directive: "Do NOT
automatically certify. Perform a real audit."). A claim is certifiable only if it is
**objectively verifiable** — by a passing test, a reproducible script, or a
registered artifact.

---

## 1. What V3 certifies

V3 is the **Operational Intelligence Platform**: a coherent, governed environment in
which the platform understands its own operation — **Events → Timelines → Workflows
→ Graph → Analytics → Recommendations** — and an operator investigates all of it
through a single **Operational Intelligence Workstation**, with every artifact
versioned, auditable, and lineage-tracked end to end back to the patient.

V3 certification makes **no real-time, autonomous-agent, multi-site, distributed,
streaming-EEG, hospital-integration, or production claim** (those are V4+). It makes
**no diagnostic or treatment claim**: analytics is *derived intelligence* and
recommendations are *operational suggestions only* — never clinical decision
support, diagnosis, or treatment, and never executed or auto-escalated.

## 2. Certification verdicts

| Verdict | Meaning |
|--------|---------|
| **CERTIFIED** | Every exit criterion is objectively verified on the authoritative inputs; no blocking gap. |
| **CERTIFIED (QUALIFIED)** | Every V3 exit criterion passes **for the delivered scope**, but one or more *foundational* dependencies inherited from V1/V2 remain provisional (see Gap Analysis). Safe for offline operational-intelligence/research; **not** a clearance for V4 or clinical use. |
| **NOT CERTIFIED** | One or more exit criteria fail. |

A QUALIFIED verdict is a real, honest outcome — not a soft pass. It names exactly
what is provisional and what must be true to reach unqualified CERTIFIED.

## 3. Audit dimensions (each scored 0–100 in the Readiness Assessment)

1. Architecture Readiness — layering/boundaries intact and enforced (incl. `frontend ↛ domain`).
2. Operational Readiness — events are first-class, immutable, observed (not owned), governed.
3. Workflow Readiness — workflows derived from events/temporal; transitions/dependencies/bottlenecks/efficiency operate.
4. Graph Readiness — the operational graph is derived (no graph-only truth), ontology-validated, queryable.
5. Analytics Readiness — derived intelligence (metrics/health/performance/quality/trend/risk); never a source of truth.
6. Recommendation Readiness — explainable, evidence-linked, analytics-linked; suggestions only; no clinical/auto-escalation.
7. Workstation Readiness — unified presentation over all six subsystems; import-pure; deterministic; six consistency checks.
8. Audit Readiness — every subsystem has an immutable, tamper-evident, verifiable audit log.
9. Governance Readiness — versioning, lineage, decisions (ADRs), quality gates operate.
10. Repository / Version Readiness — structure, tests, reproducibility, hygiene; V3 scope discipline (no forbidden V4 work).

## 4. Evidence sources (all reproducible)

- **Tests:** `python -m pytest` (boundary, determinism, per-subsystem, workstation, e2e).
- **Verification scripts:** `verify_v3_p1_p2`, `verify_v3_p3_p4`, `verify_v3_p5_p6`,
  `verify_v3_p7_p8` (objective pass/fail per criterion), plus prior `verify_v1`/`verify_v2`.
- **Registered artifacts:** event/temporal/workflow/graph/analytics/recommendation
  registries; immutable audit logs; the shared lineage graph; recorded validation
  results — surfaced through the Operational Workstation snapshot.
- **Decision records:** `.gcc/decisions/ADR-0007`…`ADR-0010`.

## 5. Scoring rubric (per dimension)

| Band | Score | Definition |
|------|-------|------------|
| Strong | 90–100 | Fully implemented, tested, reproducible, enforced. |
| Adequate | 75–89 | Implemented + tested; minor provisional aspects documented. |
| Provisional | 50–74 | Works for delivered scope; depends on a non-final foundation. |
| Weak | 25–49 | Partial; material gaps. |
| Absent | 0–24 | Not implemented. |

## 6. Certification rule

- **CERTIFIED** requires every dimension ≥ 90 **and** every exit criterion PASS
  **and** no blocking gap open.
- **CERTIFIED (QUALIFIED)** requires every *delivered-scope* exit criterion PASS,
  no dimension < 50, and every provisional item explicitly recorded in the Gap
  Analysis + Risk Review with a remediation path.
- Otherwise **NOT CERTIFIED**.

## 7. Re-certification

Any change to a certified guarantee, or the landing of a foundational dependency
(real EEG, mechanized governance, durable persistence), triggers re-running the
verification scripts + tests and re-issuing the Completion Report. Certification is
versioned with the repository.
