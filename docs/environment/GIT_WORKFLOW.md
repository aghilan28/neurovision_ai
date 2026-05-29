# GIT WORKFLOW

> **Document type:** Development Environment Foundation (V0-P7) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Environment Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Authoritative source for branch mechanics:** [`../../.gcc/BRANCH_WORKFLOW.md`](../../.gcc/BRANCH_WORKFLOW.md) (this document is the **operational, step-by-step** form; on conflict, the OS Branch Workflow governs).
> **Enforces:** Rules **NR-5, NR-7, NR-8, NR-12, NR-13, NR-14**

The concrete git procedures for each kind of work. It operationalizes the OS
[`BRANCH_WORKFLOW.md`](../../.gcc/BRANCH_WORKFLOW.md) and the
[`../governance/Change_Management.md`](../governance/Change_Management.md) router into
copy-able steps. **Never commit directly to `main`** (except the documented
bootstrap); all change arrives via a reviewed PR.

---

## 1. Branch Naming
`<type>/<short-topic>` — types: `feat/`, `arch/`, `research/`, `hotfix/`, `gov/`,
`docs/`. Phase branches may use `v<n>/<phase>` (e.g. `v0/environment-and-certification`).
- ✅ `feat/preprocessing-bandpass`, `arch/add-contracts-module`, `gov/update-risk-policy`
- ❌ `patch1`, `temp`, `myfix`

## 2. Commit Naming
`<type>(<scope>): <imperative summary>` with a body explaining **why** + refs, per
[`../../.gcc/TEMPLATES/COMMIT_MESSAGE_TEMPLATE.md`](../../.gcc/TEMPLATES/COMMIT_MESSAGE_TEMPLATE.md).
Types: `feat fix docs refactor test chore gov arch release incident`.
- A consequential commit **explains why, not just what**; architecture/governance
  commits **reference an ADR** (NR-5).

## 3. Feature Workflow (`feat/`, change class Minor/Major)
```
recover context ─► git checkout -b feat/<topic> ─► commit (annotated) ─►
self-validate (local checks/tests) ─► push ─► open PR ─► CI green ─►
human review (+ ADR if A2+) ─► merge ─► changelog + state update ─► delete branch
```

## 4. Architecture Workflow (`arch/`, A3)
RFC first → impact analysis → **ADR (Founder)** → implement on `arch/` → architecture
review + architecture audit → CI green → merge. Updates the Dependency Registry +
affected architecture docs **in the same change set** ([`../governance/Architecture_Governance.md`](../governance/Architecture_Governance.md)).

## 5. Research Workflow (`research/`, quarantine)
Exploration/experiments live on `research/` and are **not mergeable as-is**.
Insights re-enter only via a proper `feat/`/`arch/` branch with review + Lore
(capture results as a **lesson**/assumption-verification — [`../context/KNOWLEDGE_CAPTURE_FRAMEWORK.md`](../context/KNOWLEDGE_CAPTURE_FRAMEWORK.md)).

## 6. Hotfix Workflow (`hotfix/`, Emergency AE; V3+)
Mitigate the live problem → minimal safe fix → **retroactive RFC/ADR within 72h** →
deep review → reconcile. Always paired with an incident + postmortem
([`../context/POSTMORTEM_FRAMEWORK.md`](../context/POSTMORTEM_FRAMEWORK.md)).

## 7. Release Workflow
Cut from `main` only, after **release certification** ([`../quality/RELEASE_CERTIFICATION.md`](../quality/RELEASE_CERTIFICATION.md)):
gates green → version-gate checklist (if crossing a version) → **immutable tag** →
changelog/ADR links. Tags are never re-pointed.

## 8. Merge Requirements (per [`../../.gcc/BRANCH_WORKFLOW.md`](../../.gcc/BRANCH_WORKFLOW.md) §3)
A PR may merge to `main` only when: **CI green** (the workflows) · **required tests
green** (V1+) · **human review** (never AI-only, NR-7) · **ADR** if A2+ · **RFC**
trail if A2+ · **Lore + changelog** updated · affected docs updated.

## 9. Lore Requirements (every merge)
Annotated commits (why) · links to ADR/RFC/RISK/DEP · updated `CURRENT_STATE`/
registries if state changed · **AI-TRACE** for AI-authored work
([`../../.gcc/LORE_PROTOCOL.md`](../../.gcc/LORE_PROTOCOL.md)).

## 10. Governance Requirements
- Change classified ([`../governance/Change_Management.md`](../governance/Change_Management.md)); correct path followed.
- No version-skip (NR-12); in scope (NR-13).
- `arch/`+`gov/` require **Founder** ADR + review.

## 11. Approval Requirements
- Approval is **human** (Founder for A2+/architecture/governance); the **producing
  agent never approves its own change** (NR-7).
- A merge that bypasses CI/review is **reverted and recorded as an incident**.

## 12. Stacked Branches (phase work)
Phase branches may be **stacked** (a later phase based on the prior phase's branch)
so each PR shows only its own diff; the base retargets automatically as earlier PRs
merge. (This is how V0's phase PRs were structured.)

Changes to this document are governance-class and require an ADR.
