# LOCAL DEVELOPMENT

> **Document type:** Development Environment Foundation (V0-P7) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Environment Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Companion:** [`REPOSITORY_BOOTSTRAP.md`](./REPOSITORY_BOOTSTRAP.md) (the deterministic startup), [`ENVIRONMENT_VALIDATION.md`](./ENVIRONMENT_VALIDATION.md)

How to set up and run the repository **locally**, deterministically, on a fresh
machine. In **V0 there is no application code**, so local development = working with
documentation + running the same consistency checks CI runs. The procedure is
written to **extend without redesign** when V1 code arrives (the code steps are
marked **[V1+]** and activate when the toolchain lands).

> **Determinism rule:** local must match CI. If a check passes locally it must pass
> in CI and vice-versa (AP-3). Any divergence is a defect.

---

## 1. Fresh Machine Setup
**Prerequisites (V0):** Git, a POSIX shell, and standard text tooling (`grep`,
`find`, `sed`, `realpath`) — present on macOS/Linux; on Windows use WSL.
**[V1+]** Additionally: the pinned language runtime (Python), the lock-pinned
dependency manager, and a container runtime — exact versions from
[`TOOLCHAIN_STANDARD.md`](./TOOLCHAIN_STANDARD.md) (recorded by ADR at V1).

## 2. Repository Initialization
```
git clone <repo-url> neurovision_ai
cd neurovision_ai
```
**[V1+]** Create the pinned environment and install locked dependencies:
```
# example shape (exact commands set by the V1 toolchain ADR)
<version-manager> install            # install the pinned runtime
<pkg-manager> install --frozen        # install EXACT locked versions (no resolution)
<container> build .                   # optional: build the reproducible image
```

## 3. Dependency Installation
- **V0:** none (no application dependencies — [`../../.gcc/DEPENDENCY_REGISTRY.md`](../../.gcc/DEPENDENCY_REGISTRY.md) §3).
- **[V1+]:** install **only** from the lockfile (frozen/exact). Never `add latest`.
  A new dependency requires an ADR **first** ([`DEPENDENCY_MANAGEMENT.md`](./DEPENDENCY_MANAGEMENT.md)).

## 4. Environment Verification (run after init)
Run the same checks CI runs (these pass on the V0 docs-only repo):
```
# 1) required-structure: every directory has a README
for d in docs frontend backend ml preprocessing datasets evaluation \
         deployment monitoring tests tools scripts .gcc; do
  test -f "$d/README.md" || echo "MISSING README: $d"
done

# 2) broken internal links (fails build in CI documentation.yml)
#    (see .github/workflows/documentation.yml for the canonical scan)

# 3) placeholder scan (genuine unfilled markers only; mirrors documentation.yml)
grep -rnoE '<!-- *(TODO|FIXME|TBD)|<(TODO|TBD|FIXME|INSERT|PLACEHOLDER)\b|\blorem ipsum\b' docs \
  && echo "placeholder found" || echo "clean"
```
**[V1+]** also: `<pkg-manager> install --frozen` succeeds; determinism + invariant
tests green; GCC import/boundary scan green ([`ENVIRONMENT_VALIDATION.md`](./ENVIRONMENT_VALIDATION.md)).

## 5. Development Startup
1. **Recover context** — run [`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md)
   (AI agents also [`../../.gcc/AI_ONBOARDING_PROTOCOL.md`](../../.gcc/AI_ONBOARDING_PROTOCOL.md)).
2. **Confirm position** — read [`../../.gcc/CURRENT_STATE.md`](../../.gcc/CURRENT_STATE.md) + [`../../.gcc/NEXT_STATE.md`](../../.gcc/NEXT_STATE.md).
3. **Create a branch** per [`GIT_WORKFLOW.md`](./GIT_WORKFLOW.md) (`feat/`, `docs/`, …).
4. **Work within boundaries** ([`../architecture/IMPORT_RULES.md`](../architecture/IMPORT_RULES.md)); record decisions/assumptions.
5. **Self-validate** (run §4 checks; **[V1+]** tests) before opening a PR.

## 6. Troubleshooting
| Symptom | Likely cause | Action |
|---------|--------------|--------|
| A check passes locally but fails in CI | toolchain/version drift | Align versions to the pins (TOOLCHAIN_STANDARD §5/§7). |
| Broken-link check fails | a moved/renamed doc | Fix the link or add the target; re-run. |
| Placeholder check fails | a genuine unfilled placeholder marker in an authoritative doc | Complete the content (Documentation_Validation). |
| **[V1+]** `install --frozen` fails | lockfile out of date / unpinned dep | Regenerate the lock via the dependency-upgrade process (ADR). |
| **[V1+]** non-deterministic test | unseeded randomness/global state | Fix per NR-9; it is a defect, not "flaky". |

## 7. Recovery Procedures
- **Lost/unclear context:** re-run the context recovery protocol; if a doc gap is
  found, fixing it is the first action ([`../context/CONTEXT_AUDIT_SYSTEM.md`](../context/CONTEXT_AUDIT_SYSTEM.md)).
- **Corrupted local env [V1+]:** delete the local environment and re-init from the
  lockfile/container (reproducible by construction).
- **After long dormancy:** run the post-dormancy steps (recovery protocol §5):
  documentation + architecture + context audits before resuming.

## 8. Validation Procedures
Local validation must reproduce CI exactly; the authoritative gates are in
[`ENVIRONMENT_VALIDATION.md`](./ENVIRONMENT_VALIDATION.md) and
[`CI_CD_ARCHITECTURE.md`](./CI_CD_ARCHITECTURE.md). A change is ready to PR only when
its local validation is green.

Changes to this document are governance-class and require an ADR.
