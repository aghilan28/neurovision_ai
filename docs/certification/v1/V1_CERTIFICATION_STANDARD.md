# V1 Certification Standard

> **Document type:** Certification (V1) · **Status:** Authoritative for V1 audit
> **Owner:** Governance & Context Control (GCC) · **Realizes:** AP-8 (auditability), AP-9 (versioned governance), AP-11 (mechanized governance), NR-12 (version gate)
> **Companion docs:** the other files in `docs/certification/v1/`

This standard defines **what it means for Version 1 to be certified** and the
**evidence** required. Certification is **earned, not assumed** (directive:
"Do NOT automatically certify. Perform a real audit."). A claim is certifiable
only if it is **objectively verifiable** — by a passing test, a reproducible
script, or a registered artifact.

---

## 1. What V1 certifies

V1 is the **offline EEG intelligence platform**: an end-to-end, reproducible,
patient-disjoint, uncertainty-aware pipeline from raw EEG to a registered,
auditable intelligence output, plus an offline research application that presents
it. V1 certification makes **no clinical, deployment, real-time, or multi-user
claim** (those are V2–V4).

## 2. Certification verdicts

| Verdict | Meaning |
|--------|---------|
| **CERTIFIED** | Every exit criterion is objectively verified on the authoritative inputs; no blocking gap. |
| **CERTIFIED (QUALIFIED)** | The implemented offline pipeline meets every exit criterion **for its delivered scope**, but one or more *foundational* dependencies are provisional (see Gap Analysis). Safe to use offline for research; **not** a clearance for V2. |
| **NOT CERTIFIED** | One or more exit criteria fail. |

A QUALIFIED verdict is a real, honest outcome — not a soft pass. It names exactly
what is provisional and what must be true to reach unqualified CERTIFIED.

## 3. Audit dimensions (each scored 0–100 in the Readiness Assessment)

1. Architecture Readiness — layering/boundaries intact and enforced.
2. Scientific Readiness — methods are sound and correctly applied.
3. Evaluation Readiness — patient-disjoint evaluation works and is enforced.
4. Model Readiness — baselines train, predict, are registered and reproducible.
5. Calibration Readiness — calibration + conformal + coverage work and are validated.
6. Application Readiness — offline app presents registered artifacts faithfully.
7. Governance Readiness — versioning, lineage, decisions, quality gates operate.
8. Repository Readiness — structure, tests, reproducibility, hygiene.
9. Version Readiness — V1 scope discipline; no forbidden V2+ work.

## 4. Evidence sources (all reproducible)

- **Tests:** `python -m pytest` (determinism, patient-disjoint, boundary, e2e).
- **Verification scripts:** `python -m scripts.verify_v1_p5_p6` and
  `python -m scripts.verify_v1` (objective pass/fail per criterion).
- **Registered artifacts:** inference runs under the artifact store
  (`inference_index.json`, registries, lineage, reports) with sha256 checksums.
- **Decision records:** `.gcc/decisions/ADR-0001`, `ADR-0002`.

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

Any change to a certified guarantee, or landing of a foundational dependency,
triggers re-running the verification scripts + tests and re-issuing the
Completion Report. Certification is versioned with the repository.
