# V2 Certification Standard

> **Document type:** Certification (V2) · **Status:** Authoritative for V2 audit
> **Owner:** Governance & Context Control (GCC) · **Realizes:** AP-8 (auditability), AP-9 (versioned governance), AP-11 (mechanized governance), NR-12 (version gate)
> **Companion docs:** the other files in `docs/certification/v2/`

This standard defines **what it means for Version 2 to be certified** and the
**evidence** required. Certification is **earned, not assumed** (directive: "Do
NOT automatically certify. Perform a real audit."). A claim is certifiable only if
it is **objectively verifiable** — by a passing test, a reproducible script, or a
registered artifact.

---

## 1. What V2 certifies

V2 is the **Clinical Workflow Platform**: a coherent, governed environment in
which a reviewer navigates **Patient → Case → Study → Review → Finding →
Interpretation → Knowledge → Multi-Case Intelligence → Decision Support** through
a single Clinical Workstation, with every artifact versioned, auditable, and
lineage-tracked end to end.

V2 certification makes **no clinical-deployment, real-time, hospital-integration,
or multi-user-production claim** (those are V3–V4). It also makes **no diagnostic
or treatment claim**: the platform is decision *support* only — the clinician
remains the decision-maker.

## 2. Certification verdicts

| Verdict | Meaning |
|--------|---------|
| **CERTIFIED** | Every exit criterion is objectively verified on the authoritative inputs; no blocking gap. |
| **CERTIFIED (QUALIFIED)** | Every V2 exit criterion passes **for the delivered scope**, but one or more *foundational* dependencies inherited from V1 remain provisional (see Gap Analysis). Safe for offline workflow/research; **not** a clearance for V3 or clinical use. |
| **NOT CERTIFIED** | One or more exit criteria fail. |

A QUALIFIED verdict is a real, honest outcome — not a soft pass. It names exactly
what is provisional and what must be true to reach unqualified CERTIFIED.

## 3. Audit dimensions (each scored 0–100 in the Readiness Assessment)

1. Architecture Readiness — layering/boundaries intact and enforced (incl. `frontend ↛ domain`).
2. Workflow Readiness — case/review/finding lifecycles operate and are governed.
3. Clinical Readiness — clinical-case/review/finding semantics are sound for the delivered scope.
4. Knowledge Readiness — terminology/concepts/taxonomy/relationships operate, are versioned and audited.
5. Decision Support Readiness — explainable, evidence-linked, scope-guarded; no diagnosis/treatment.
6. Audit Readiness — every subsystem has an immutable, tamper-evident, verifiable audit log.
7. Governance Readiness — versioning, lineage, decisions, quality gates operate.
8. Repository Readiness — structure, tests, reproducibility, hygiene.
9. Version Readiness — V2 scope discipline; no forbidden V3+ work.

## 4. Evidence sources (all reproducible)

- **Tests:** `python -m pytest` (boundary, determinism, per-subsystem, workstation, e2e).
- **Verification scripts:** `python -m scripts.verify_v2_p3_p4`,
  `python -m scripts.verify_v2_p5_p6`, `python -m scripts.verify_v2_p7_p8`
  (objective pass/fail per criterion), plus `python -m scripts.verify_v2`.
- **Registered artifacts:** case/review/finding/knowledge/intelligence/decision
  registries; immutable audit logs; the shared lineage graph; recorded validation
  results — surfaced through the Clinical Workstation snapshot.
- **Decision records:** `.gcc/decisions/ADR-0003`, `ADR-0004`, `ADR-0005`, `ADR-0006`.

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
