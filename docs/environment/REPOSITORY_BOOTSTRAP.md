# REPOSITORY BOOTSTRAP

> **Document type:** Development Environment Foundation (V0-P7) · **Tier 2**
> **Status:** Authoritative — a **deterministic** startup process.
> **Owner:** Founder (Environment Owner role)
> **Update procedure:** Governance-class change (ADR) — the sequence must stay stable.
> **Companions:** [`LOCAL_DEVELOPMENT.md`](./LOCAL_DEVELOPMENT.md), [`ONBOARDING_WORKFLOW.md`](./ONBOARDING_WORKFLOW.md), [`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md)

The **single deterministic path** from "nothing" to "ready to work." A completely
new developer **or AI agent** must be able to **clone → initialize → validate →
recover context → begin work — without asking questions.** Follow these steps in
order; each has a clear success signal.

> **Determinism guarantee:** same steps, same order ⇒ same ready state, every time,
> for every agent. If a step needs a question answered that isn't in the repo, that
> gap is a defect — fixing it is the first contribution.

---

## Step 0 — Prerequisites
Have Git + a POSIX shell (macOS/Linux, or WSL on Windows). **[V1+]** also the pinned
toolchain ([`TOOLCHAIN_STANDARD.md`](./TOOLCHAIN_STANDARD.md)). No other knowledge
required.

## Step 1 — Clone
```
git clone <repo-url> neurovision_ai
cd neurovision_ai
```
**Success:** the repository is present with `docs/`, the module directories, `.gcc/`,
and `.github/`.

## Step 2 — Initialize Environment
- **V0 (docs-only):** nothing to install.
- **[V1+]:** create the pinned environment and install **locked** dependencies
  (`<pkg-manager> install --frozen`) / build the container
  ([`LOCAL_DEVELOPMENT.md`](./LOCAL_DEVELOPMENT.md) §2).
**Success:** environment matches the pins (no resolution drift).

## Step 3 — Validate Environment
Run the environment validation gates ([`ENVIRONMENT_VALIDATION.md`](./ENVIRONMENT_VALIDATION.md)):
```
# structure: every required directory has a governance README
for d in docs frontend backend ml preprocessing datasets evaluation \
         deployment monitoring tests tools scripts .gcc; do
  test -f "$d/README.md" || echo "MISSING README: $d"
done
# documentation + architecture + governance + context checks mirror CI:
#   see .github/workflows/{documentation,architecture,governance,context}.yml
```
**Success:** no MISSING output; the CI-equivalent checks are clean (EV-2…EV-5).

## Step 4 — Recover Context
Run the **deterministic** recovery sequence — this is the heart of bootstrap:
1. Read [`../../.gcc/MAIN_CONTEXT.md`](../../.gcc/MAIN_CONTEXT.md).
2. Execute [`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md)
   (its 16-step read order).
3. **AI agents:** also complete [`../../.gcc/AI_ONBOARDING_PROTOCOL.md`](../../.gcc/AI_ONBOARDING_PROTOCOL.md).
4. Read [`../../.gcc/CURRENT_STATE.md`](../../.gcc/CURRENT_STATE.md) + [`../../.gcc/NEXT_STATE.md`](../../.gcc/NEXT_STATE.md).
**Success:** you can answer the recovery validation questions (recovery protocol §3)
**from the repository alone** — no external conversation.

## Step 5 — Begin Work
1. Confirm the task is **in scope** (NR-13) and **version-gate valid** (NR-12).
2. Create a branch per [`GIT_WORKFLOW.md`](./GIT_WORKFLOW.md).
3. Work within boundaries ([`../architecture/IMPORT_RULES.md`](../architecture/IMPORT_RULES.md));
   record decisions/assumptions; emit AI-TRACE (if AI).
4. Self-validate (local checks/tests) → open a PR → CI + human review.
**Success:** a compliant PR that passes all required gates.

## Bootstrap Validation Checklist
- [ ] Clone present with all top-level directories.
- [ ] Environment initialized (V0: n/a; **[V1+]** frozen install/container build OK).
- [ ] Structure + documentation + architecture + governance + context checks clean.
- [ ] Context recovered; recovery validation questions answered from the repo alone.
- [ ] Current/next state read; task confirmed in scope + version-valid.
- [ ] Branch created per the git workflow.

A failure at any step is **not** "ask the founder" — it is either a documented
troubleshooting case ([`LOCAL_DEVELOPMENT.md`](./LOCAL_DEVELOPMENT.md) §6) or a doc
gap to fix (then the next agent succeeds).

Changes to this document are governance-class and require an ADR.
