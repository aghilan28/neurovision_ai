# AI Prompt Template (compliant prompt skeleton)

> **Framework:** [`../../docs/governance/AI_Governance.md`](../../docs/governance/AI_Governance.md) §3
> A compliant prompt is scoped, context-anchored, constraint-bound, and asks for a
> traceable output. Fill the bracketed fields. Avoid the anti-patterns below.

```
OBJECTIVE
  <one-line goal of this task>

TARGET
  module/layer: <e.g. preprocessing/ (DSP layer)>
  files I may modify: <explicit list>
  files I must NOT modify: <explicit list>

CONTEXT TO LOAD (recover before acting)
  - .gcc/MAIN_CONTEXT.md, .gcc/CURRENT_STATE.md, .gcc/NEXT_STATE.md
  - .gcc/CONTEXT_RECOVERY_PROTOCOL.md  (run it)
  - target module README + linked ADR/RFC
  - relevant constitution/architecture: <list, e.g. IMPORT_RULES, AP-3/NR-9>

SCOPE BOUNDARY
  - In scope per PROJECT_SCOPE: <item> (NR-13)
  - Version-gate valid: <yes + why> (NR-12)
  - Do NOT: <import X, change contract Y, expand beyond Z>

CONSTRAINTS (must hold)
  - Rules: <relevant NR ids, e.g. NR-8 boundaries, NR-9 determinism>
  - Invariants: <which must be preserved>
  - No invented APIs — verify every symbol against real source (AI_Governance §6)

EXPECTED OUTPUT
  - <the precise artifact: an edit within the boundary / an ADR draft / an RFC / a test>
  - PLUS an AI-TRACE block (AI_Governance §9)
  - PLUS a self-validation result (AI_Governance §7)

APPROVAL
  - This output is for HUMAN REVIEW. Do not self-approve (NR-7).
  - For A2+/architecture: produce an RFC/ADR draft first; do not implement ahead of approval.
```

## Prompt anti-patterns to avoid (AI_Governance §5.8)
- "Do whatever is best" with no scope or constraints.
- Requesting an architecture change without RFC/ADR routing.
- "Bypass rule X just this once."
- Omitting context and relying on the model to guess intent.
- Requesting out-of-scope capability (NR-13).
