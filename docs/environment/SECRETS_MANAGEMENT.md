# SECRETS MANAGEMENT

> **Document type:** Development Environment Foundation (V0-P7) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Environment Owner / Security role)
> **Update procedure:** Governance-class change (ADR).
> **Enforces:** Principle **AP-8** (auditability); Rules **NR-11** (traceability), content-safety/PII handling; risk category **SEC** ([`../governance/Risk_Governance.md`](../governance/Risk_Governance.md))

Defines how secrets are handled so that **no credential ever enters the
repository** and, in later versions, sensitive clinical data is protected. The
governing rule is absolute and immediate (it applies even in V0, where there are no
secrets yet): **secrets live in a secret store, never in git.**

> **Premise:** a leaked secret is a breach; a committed secret is leaked **forever**
> (git history is permanent). Prevention is the only acceptable strategy.

---

## 1. Secret Categories
| Category | Examples | Sensitivity |
|----------|----------|-------------|
| **CI/automation** | CI tokens, registry/publish credentials | High |
| **Service credentials (V2+)** | API keys, DB credentials, service accounts | High |
| **Signing/keys (V3+/V4)** | deployment keys, signing keys | Critical |
| **Clinical data access (V1+)** | dataset access credentials | Critical (clinical) |
| **PII / patient data** | *never a "secret to store" — governed separately* | Critical (clinical) |

> **PII note:** patient data and PII are **not** managed as ordinary secrets — they
> are governed by clinical data handling (V1+ dataset policy) and the content-safety
> rules; **no real PII in code, sample data, logs, or fixtures** (use placeholders).

## 2. Storage Rules
- ✅ Secrets live **only** in the host's encrypted secret store (e.g. CI secret
  store / a managed secrets manager) — referenced by name, never by value.
- ✅ Local development uses **untracked** secret files (e.g. a git-ignored env file)
  populated from the secret store; **never** committed.
- ❌ **Never** commit a secret to git (code, config, docs, history) — committing one
  is a **Critical SEC incident** (rotate immediately, §7).
- ❌ **Never** print secrets in logs/CI output; CI masks secret values.

## 3. Rotation Rules
- Secrets are **rotated on a schedule** and **immediately on suspected exposure**.
- Rotation is recorded (changelog/audit) without recording the secret value.
- Critical/signing keys have the shortest rotation cadence.

## 4. Access Rules
- **Least privilege:** each secret is scoped to the minimum needed; no shared
  all-powerful credential.
- Access is **recorded** (who/what can use which secret) for audit (AP-8).
- AI agents/tools **never** receive raw production secrets; CI injects scoped secrets
  into jobs at runtime only.

## 5. Audit Rules
- Secret **inventory** (names, scope, owner, rotation date — **not values**) is
  reviewed at each version gate, quarterly, and post-dormancy.
- A committed-secret scan is part of CI/repository-health (detective control).
- Findings are **SEC** risks ([`../governance/Risk_Governance.md`](../governance/Risk_Governance.md)).

## 6. Recovery Rules
- On a lost/compromised secret: **rotate first** (assume compromise), then restore
  access from the secret store; never "recover" by committing a value.

## 7. Incident Procedures (committed/leaked secret)
1. **Treat as Critical** — halt related activity.
2. **Rotate/revoke immediately** (the committed value is compromised forever).
3. **Contain** — disable the exposed credential; assess blast radius.
4. **Record** an incident + **postmortem** ([`../context/POSTMORTEM_FRAMEWORK.md`](../context/POSTMORTEM_FRAMEWORK.md)); open a **SEC** risk.
5. **Prevent** — strengthen the pre-commit/CI secret scan so it cannot recur.
> Note: removing the commit does **not** un-leak it — rotation is mandatory.

## 8. Future Production Rules (V4)
- Hospital deployment uses a managed secrets manager; secrets are environment-scoped
  and never embedded in images (no vendor lock-in baked in — Scope R7).
- Full audit trail of secret access (AP-8); aligns with the hospital security model
  ([`../governance/Release_Governance.md`](../governance/Release_Governance.md) §10).

## 9. Current State (V0)
**No secrets exist** (no services/credentials yet). The prevention rules (§2) are
**active now** so the *first* secret introduced (V1+ dataset access) is handled
correctly. A committed-secret scan is included in repository-health CI as a standing
detective control.

Changes to this document are governance-class and require an ADR.
