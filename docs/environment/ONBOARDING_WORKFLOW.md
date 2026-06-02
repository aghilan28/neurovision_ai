# ONBOARDING WORKFLOW

> **Document type:** Development Environment Foundation (V0-P7) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Environment Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Companions:** [`REPOSITORY_BOOTSTRAP.md`](./REPOSITORY_BOOTSTRAP.md), [`../../.gcc/AI_ONBOARDING_PROTOCOL.md`](../../.gcc/AI_ONBOARDING_PROTOCOL.md), [`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md)

The structured path that takes a new contributor (human or AI) from "cloned the
repo" to "productive and safe." Bootstrap ([`REPOSITORY_BOOTSTRAP.md`](./REPOSITORY_BOOTSTRAP.md))
gets the environment ready; **onboarding gets the *contributor* ready** —
understanding the architecture, governance, context, and quality well enough to not
cause drift. Each track ends in a **validation checkpoint**.

> **Premise:** the difference between a contributor who strengthens the repository
> and one who quietly erodes it is onboarding. It is mandatory, deterministic, and
> self-validating.

---

## 1. Onboarding Tracks (do in order)

### Track A — Developer Onboarding (human)
1. Bootstrap the repo ([`REPOSITORY_BOOTSTRAP.md`](./REPOSITORY_BOOTSTRAP.md)).
2. Read the constitution (vision → objectives → scope → version model → principles →
   rules → glossary).
3. Internalize the **12 principles** and **15 rules**.
4. Learn the **standards** ([`DEVELOPMENT_STANDARDS.md`](./DEVELOPMENT_STANDARDS.md))
   and the **git workflow** ([`GIT_WORKFLOW.md`](./GIT_WORKFLOW.md)).
- **Checkpoint A:** can state what the project is/isn't, the current version/phase,
  five rules + the principle each enforces, and how to open a compliant PR.

### Track B — AI Onboarding (agent)
1. Complete [`../../.gcc/AI_ONBOARDING_PROTOCOL.md`](../../.gcc/AI_ONBOARDING_PROTOCOL.md)
   **in full** (it is the hard gate; reading allowed before completion, changing not).
2. Accept the operating contract (recover context, no invented APIs, stay in scope/
   version, AI-TRACE, **never self-approve**).
- **Checkpoint B:** passes the AI onboarding validation (recovery §3 questions +
  AI-specific questions); **not cleared to change anything until passed**.

### Track C — Architecture Onboarding
1. Read [`../architecture/`](../architecture/) (layered → system context → module
   boundaries → dependency graph → import rules).
2. Learn the **DAG** and the forbidden imports (`frontend`→domain; `preprocessing`→anything).
- **Checkpoint C:** can state the dependency direction and name a forbidden import;
  can find the README/contract of any module before touching it.

### Track D — Governance Onboarding
1. Read [`../governance/README.md`](../governance/README.md) (start there) and the
   change router ([`../governance/Change_Management.md`](../governance/Change_Management.md)).
2. Learn **RFC → ADR**, review depth, and that A2+/architecture = Founder approval.
- **Checkpoint D:** can classify a change and say what records it must leave (ADR,
  changelog, registries).

### Track E — Context Onboarding
1. Read [`../context/README.md`](../context/README.md) and [`../../.gcc/LORE_PROTOCOL.md`](../../.gcc/LORE_PROTOCOL.md).
2. Learn the capture loop and the memory systems (decision/risk/assumption/lesson/
   postmortem) + retention (append-only; never delete the why).
- **Checkpoint E:** can say where each kind of knowledge is captured and why nothing
  important may live only in a chat.

### Track F — Quality Onboarding
1. Read [`../quality/README.md`](../quality/README.md): the gates (G1–G8), validation
   (VC-*), the per-domain review checklists, and metrics (M1–M12 + RQI).
2. Learn that clinical-safety/validation-integrity gates are **never waivable**.
- **Checkpoint F:** can name the gates a given change must pass and what evidence
  each requires.

## 2. Reading Order (canonical, deterministic)
This mirrors [`../README.md`](../README.md) and [`../../.gcc/MAIN_CONTEXT.md`](../../.gcc/MAIN_CONTEXT.md) §15:
```
MAIN_CONTEXT → CONTEXT_RECOVERY_PROTOCOL (+ AI_ONBOARDING for agents) →
CURRENT_STATE → NEXT_STATE → VERSION_STATUS →
constitution (vision→objectives→scope→version model→principles→rules→glossary) →
architecture/ → governance/ → quality/ → context/ →
registries (.gcc: decisions/risks/assumptions/dependencies) →
KNOWLEDGE_GRAPH → context/REPOSITORY_KNOWLEDGE_MODEL → task-local module README + ADRs
```

## 3. Validation Checkpoints (gate to "productive")
A contributor is **cleared to contribute** only after passing the checkpoints for
their tracks (A or B, plus C–F). The objective bar = the recovery validation
questions ([`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md) §3)
+ the per-track checkpoint above. Failing a checkpoint = re-read the mapped source
(or fix the doc gap); **never proceed by guessing.**

## 4. First Contribution
Prefer a **small, in-boundary, low-risk** first change (e.g. a docs fix or a single
in-boundary unit) to exercise the full loop: recover → plan → produce →
self-validate → trace → PR → review. Anything **A2+** starts with an RFC/ADR draft.

## 5. Relationship To Other Documents
- Bootstrap/local: [`REPOSITORY_BOOTSTRAP.md`](./REPOSITORY_BOOTSTRAP.md), [`LOCAL_DEVELOPMENT.md`](./LOCAL_DEVELOPMENT.md)
- AI/context: [`../../.gcc/AI_ONBOARDING_PROTOCOL.md`](../../.gcc/AI_ONBOARDING_PROTOCOL.md), [`../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md`](../../.gcc/CONTEXT_RECOVERY_PROTOCOL.md)
- Quality/governance/architecture indexes in [`../`](../)

Changes to this document are governance-class and require an ADR.
