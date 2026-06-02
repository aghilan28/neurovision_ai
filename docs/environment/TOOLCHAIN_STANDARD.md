# TOOLCHAIN STANDARD

> **Document type:** Development Environment Foundation (V0-P7) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Environment Owner role)
> **Update procedure:** Governance-class change (ADR); adding/removing a tool is an **A2+** change (Dependency Registry).
> **Enforces:** AP-6 (reproducibility), AP-11 (mechanization), AP-12 (survivability); Scope R7 (no lock-in)
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

Defines the **tools** the project uses and how they are versioned, updated, and kept
compatible — so the toolchain is **reproducible** and does not drift. Concrete
version pins for code toolchains are recorded by **ADR at the point each is
introduced** (pinning now, with no code, would be premature and stale); the
**strategy** here is binding immediately.

---

## 1. Required Tools (V0, active now)
| Tool | Purpose | Notes |
|------|---------|-------|
| **Git** | Version control; history-as-record | Branch workflow ([`GIT_WORKFLOW.md`](./GIT_WORKFLOW.md)) |
| **GitHub Actions (CI)** | Mechanize the quality gates | Workflows in [`../../.github/workflows/`](../../.github/workflows/) |
| **A POSIX shell + standard text tooling** | Run doc/consistency checks | Used by the V0 workflows |
| **Markdown** | All V0 documentation | Lint/link checks in `documentation.yml` |

## 2. Required Tools (V1+, introduced by ADR when code begins)
| Tool class | Anticipated | Strategy |
|------------|-------------|----------|
| **Language runtime (ML/DSP/backend)** | **Python** | Single pinned minor version (§5); managed via a version manager + lockfile. |
| **Package/dependency manager** | a lockfile-producing manager | Deterministic, lock-pinned installs (§ [`DEPENDENCY_MANAGEMENT.md`](./DEPENDENCY_MANAGEMENT.md)). |
| **Container runtime** | OCI containers | Reproducible build/run parity with CI (§4 container strategy). |
| **Test runner** | language-native | `--run`/single-shot in CI (no watch mode). |
| **Frontend toolchain (V2+)** | **TypeScript** + a pinned package manager | Introduced at V2 by ADR. |

## 3. Optional Tools
- Editor/IDE of choice (incl. **Cursor**) — personal preference, must not change
  repository outputs or bypass gates.
- Local markdown linters, link checkers, pre-commit helpers (must mirror CI logic).

## 4. Approved Tools (AI + MCP)
- **Approved AI systems:** Claude, Codex, Cursor, Kiro, MCP tools, and future systems
  added by ADR — exactly the set in [`../governance/AI_Governance.md`](../governance/AI_Governance.md) §1.
- **AI tooling standard:** every AI tool operates under the AI governance (context
  recovery, anti-hallucination, AI-TRACE, human approval — NR-7). Tool output is
  **untrusted input** until validated ([`../quality/AI_OUTPUT_VALIDATION.md`](../quality/AI_OUTPUT_VALIDATION.md)).
- **MCP standard:** MCP servers/tools **provide context and run checks**; they have
  **no authority**, must not execute unreviewed commands, and are recorded in the
  AI-TRACE (`context-read`) of any change they informed.

## 5. Version Policy
- **One pinned version per toolchain** (e.g. a single Python minor), recorded by ADR
  and in the Dependency Registry; CI uses the **same** pin as local (parity).
- Versions are **explicit and reproducible** — never "latest".
- A version change is an **A2+** change (ADR + Dependency Registry + changelog).

## 6. Update Policy
- Updates follow [`DEPENDENCY_MANAGEMENT.md`](./DEPENDENCY_MANAGEMENT.md) (upgrade
  strategy): scheduled, reviewed, lock-pinned, validated by CI before merge.
- Security updates are prioritized (handled as a risk; [`../governance/Risk_Governance.md`](../governance/Risk_Governance.md) **SEC**).
- No update merges if it breaks an invariant test or reproducibility.

## 7. Compatibility Policy
- Local and CI **must** run the same toolchain versions (determinism, AP-3).
- Container images pin the full toolchain so "works on my machine" cannot occur.
- Backward compatibility of contracts is required across a version line; breaking a
  contract is an **A2/A3** change (ADR).

## 8. Forbidden Tools / Practices
- ❌ Any tool that introduces **non-determinism** on a reproducible path (NR-9).
- ❌ **Unpinned/"latest"** dependencies (AP-6).
- ❌ Tools that require **vendor/hardware lock-in** as an architectural assumption (Scope R7).
- ❌ Any AI tool used to **bypass review/gates** or auto-merge (NR-7).
- ❌ Committing **secrets** or secret-bearing tool config ([`SECRETS_MANAGEMENT.md`](./SECRETS_MANAGEMENT.md)).
- ❌ Tools that smuggle a **forbidden cross-module dependency** into production (NR-8).

## 9. Environment Standard (parity)
The authoritative environment is defined by pinned toolchain + lockfiles +
container spec (introduced with V1 code). Until then, the V0 environment is the
**documentation/CI toolchain** above, which is already deterministic. See
[`LOCAL_DEVELOPMENT.md`](./LOCAL_DEVELOPMENT.md) and [`ENVIRONMENT_VALIDATION.md`](./ENVIRONMENT_VALIDATION.md).

## 10. Relationship To Other Documents
- Dependencies: [`DEPENDENCY_MANAGEMENT.md`](./DEPENDENCY_MANAGEMENT.md), [`../../.gcc/DEPENDENCY_REGISTRY.md`](../../.gcc/DEPENDENCY_REGISTRY.md)
- CI: [`CI_CD_ARCHITECTURE.md`](./CI_CD_ARCHITECTURE.md) · AI/MCP: [`../governance/AI_Governance.md`](../governance/AI_Governance.md)

Changes to this document are governance-class and require an ADR.
