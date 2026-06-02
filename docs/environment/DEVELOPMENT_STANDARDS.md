# DEVELOPMENT STANDARDS

> **Document type:** Development Environment Foundation (V0-P7) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Environment Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Enforces / inherits:** the constitution (AP-1…AP-12 / NR-1…NR-15), [`../quality/`](../quality/), [`../governance/`](../governance/)
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

The standards every contributor (human or AI) follows. Each standard is stated with
**explicit examples** and **anti-patterns** so it is unambiguous. Most code-level
standards are **V1+** (no code in V0) but are authoritative now so the *first* line
of code conforms.

> **Premise:** standards exist to make the repository **uniform, reviewable, and
> survivable.** A standard without an example is a suggestion; every standard here
> has a concrete do/don't.

---

## 1. Coding Standards (V1+)
- **Determinism on production paths** (AP-3/NR-9): no unseeded randomness, wall-clock
  dependence, or ordering-dependent global state in `preprocessing/` or any
  reproducible path.
- **Boundaries respected** (NR-8): a file only imports what its module is allowed to
  ([`../architecture/IMPORT_RULES.md`](../architecture/IMPORT_RULES.md)).
- **Uncertainty + provenance preserved** in any clinical path (NR-4/NR-11).
- **Typed and documented** public interfaces; small, single-responsibility units.
- **No PII in code/sample data**; use generic placeholders.
  - ✅ *Example:* a seeded band-pass filter in `preprocessing/` with pinned
    coefficients returning identical output across runs.
  - ❌ *Anti-pattern:* `import ml` inside `frontend/`; an unseeded `random` augmentation
    on the production path; logging a patient identifier.

## 2. Repository Standards
- Every directory has a **governance README** with Owner + boundary rules (V0-P2).
- **Single canonical source** per fact (Documentation_Governance §2); link, don't duplicate.
- Infrastructure (`.github/`, `.gcc/`, `tools/`, `scripts/`) is **never imported by
  production** (NR-8).
  - ✅ *Example:* a new module ships with its README, tests, and Dependency-Registry update.
  - ❌ *Anti-pattern:* a "misc/" or "utils/" dumping ground that everything imports.

## 3. Naming Standards
- **Branches:** `<type>/<short-topic>` — `feat/`, `arch/`, `research/`, `hotfix/`,
  `gov/`, `docs/` ([`GIT_WORKFLOW.md`](./GIT_WORKFLOW.md)).
- **Commits:** `<type>(<scope>): <imperative summary>` ([`../../.gcc/TEMPLATES/COMMIT_MESSAGE_TEMPLATE.md`](../../.gcc/TEMPLATES/COMMIT_MESSAGE_TEMPLATE.md)).
- **IDs:** `ADR-NNNN`, `RFC-NNNN`, `RISK-NNNN`, `ASM-NNNN`, `DEP-NNNN`, `PM-NNNN`,
  `LEARN-NNNN` (zero-padded, monotonic).
- **Files:** module docs `UPPER_SNAKE.md` for canonical docs; code naming per the
  language standard adopted at V1 (recorded by ADR).
  - ✅ *Example:* `feat/preprocessing-bandpass`, `arch(evaluation): add site-disjoint folds`.
  - ❌ *Anti-pattern:* `fix2`, `temp`, `final-final`, ambiguous commit "update stuff".

## 4. Testing Standards (V1+)
- Governed by [`../quality/TEST_STRATEGY.md`](../quality/TEST_STRATEGY.md) and
  [`../governance/Testing_Governance.md`](../governance/Testing_Governance.md).
- **Invariant behaviors 100% tested**; determinism tests for preprocessing;
  patient-disjoint assertions in evaluation; **never disable a guarding test** (NR-2).
  - ✅ *Example:* a test asserting no patient ID appears in both train and test.
  - ❌ *Anti-pattern:* `@skip` on a failing boundary test to make CI green.

## 5. Documentation Standards
- Governed by [`../quality/DOCUMENTATION_VALIDATION.md`](../quality/DOCUMENTATION_VALIDATION.md):
  complete (no placeholders), singular, consistent, fresh, traceable, owned.
- New term → **Glossary** in the same change (NR-14).
  - ✅ *Example:* a module README updated in the same PR that changes its boundary.
  - ❌ *Anti-pattern:* "TODO: document later"; a second copy of a fact that drifts.

## 6. AI Development Standards
- Governed by [`../governance/AI_Governance.md`](../governance/AI_Governance.md) +
  [`../quality/AI_OUTPUT_VALIDATION.md`](../quality/AI_OUTPUT_VALIDATION.md).
- **Recover context first**, verify every symbol (no hallucinated APIs), stay in
  scope/version, emit the **AI-TRACE** block, **never self-approve** (NR-7).
  - ✅ *Example:* an AI PR with an accurate AI-TRACE, all references resolving, a human reviewer.
  - ❌ *Anti-pattern:* AI output merged with no review; invented function names; silent scope expansion.

## 7. Review Standards
- Governed by [`../governance/Review_Governance.md`](../governance/Review_Governance.md)
  and the per-domain [`../quality/CODE_REVIEW_CHECKLISTS.md`](../quality/CODE_REVIEW_CHECKLISTS.md).
- Risk-based depth (A0→A3); human approval (NR-7); architecture changes = Founder.

## 8. Release Standards
- Governed by [`../governance/Release_Governance.md`](../governance/Release_Governance.md)
  and [`../quality/RELEASE_CERTIFICATION.md`](../quality/RELEASE_CERTIFICATION.md).
- Reproducible build; immutable tags; tested rollback; no version-skip (NR-12).

## 9. Future ML Standards (V1+)
- Patient-disjoint evaluation only (NR-3); calibrated uncertainty + abstention (NR-4);
  reproducible training (NR-10); model cards; provenance on outputs.
  - ❌ *Anti-pattern:* reporting accuracy on a random segment split.

## 10. Future Clinical Standards (V2+)
- Decision-support only (clinician decides); faithful uncertainty in the UI;
  end-to-end traceability/audit; no autonomous clinical action (Scope O5/R1).

## 11. Enforcement
These standards are enforced by review ([`../governance/Review_Governance.md`](../governance/Review_Governance.md)),
the quality gates (G1–G8), and the CI workflows ([`CI_CD_ARCHITECTURE.md`](./CI_CD_ARCHITECTURE.md)).
A standard violation is handled per [`../quality/FAILURE_HANDLING.md`](../quality/FAILURE_HANDLING.md).

Changes to this document are governance-class and require an ADR.
