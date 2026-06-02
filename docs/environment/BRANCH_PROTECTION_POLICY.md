# BRANCH PROTECTION POLICY

> **Document type:** Development Environment Foundation (V0-P7) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Environment Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Enforces:** Rules **NR-5, NR-7, NR-8, NR-12**; mechanizes the quality gates ([`../quality/QUALITY_GATES.md`](../quality/QUALITY_GATES.md))

Defines what protects the trunk so that **nothing reaches `main` without passing the
gates and a human review.** These are the settings the repository host (GitHub)
must enforce, plus the policy behind them. They make the governance/quality rules
**mechanical** (AP-11), not merely aspirational.

---

## 1. Protected Branches
- **`main`** — the always-releasable, governed trunk. **Protected.**
- **Release tags** (`v*`) — **immutable** once created (Release_Governance §6).
- **Phase/long-lived integration branches** (e.g. `v0/*`) — protected while they
  serve as a PR base.

## 2. Merge Restrictions (on `main`)
- ❌ **No direct pushes** to `main` (except the one-time bootstrap commit).
- ❌ **No force-push** / no history rewrite on `main`.
- ✅ **PR-only** merges; **linear history** preferred (squash/rebase per repo setting).
- ✅ Branch must be **up to date** with `main` before merge.

## 3. Required Status Checks (CI must pass — see [`CI_CD_ARCHITECTURE.md`](./CI_CD_ARCHITECTURE.md))
A PR to `main` is blocked unless **all required workflows are green**:
- `documentation` (G2 — links/placeholders/terms/ownership)
- `architecture` (G1 — structure/boundaries/acyclicity)
- `governance` (G8 — change-class/ADR/no stray IDs)
- `context` (G7 — registries/decisions/assumptions present + fresh)
- `repository-health` (aggregate; on schedule + on demand)
- **[V1+]** `quality` (G4/G5 — tests/coverage/validation) once code exists.

## 4. Review Requirements
- **≥1 human approving review** on every PR; **the producing agent may not approve
  its own change** (NR-7).
- **Architecture (`arch/`) and Governance (`gov/`) PRs require Founder approval** + an
  approved **ADR** (A3).
- Review depth is risk-based ([`../governance/Review_Governance.md`](../governance/Review_Governance.md) §4);
  AI-generated PRs also pass the AI review gate (G3).

## 5. Quality Gates (enforced at merge)
The eight gates ([`../quality/QUALITY_GATES.md`](../quality/QUALITY_GATES.md)) apply
by change type; the **clinical-safety and validation-integrity gates (G5 clinical,
G4 invariants) are never waivable.** A gate exception requires a Founder ADR with a
compensating control + expiry (§7).

## 6. Approval Requirements (summary)
| PR type | Required | Approver |
|---------|----------|----------|
| docs / minor | CI green + review | Reviewer (Founder) |
| major (A2) | + ADR + Dependency Registry | Founder |
| architecture / governance (A3) | + RFC + ADR + audit | **Founder (mandatory)** |
| release / version gate | + release certification + version-gate ADR | Founder |

## 7. Emergency Procedures (V3+)
- A genuine emergency (live, patient-affecting problem) may use a `hotfix/` with an
  **expedited** path: minimal safe review now, **retroactive RFC/ADR within 72h**,
  full review + reconciliation after.
- An emergency **never** silently bypasses gates: the bypass is **recorded as an
  incident** + postmortem, and the skipped checks are run post-hoc.
- **No emergency waives** clinical-safety/validation-integrity gates.

## 8. Enforcement & Drift
- These settings are configured on the host and mirrored here as policy; a drift
  between host settings and this policy is a **governance defect** to reconcile.
- A merge that reached `main` bypassing protection is a **governance failure**
  ([`../quality/FAILURE_HANDLING.md`](../quality/FAILURE_HANDLING.md) §2.4): revert,
  incident, postmortem, strengthen the control.

Changes to this document are governance-class and require an ADR.
