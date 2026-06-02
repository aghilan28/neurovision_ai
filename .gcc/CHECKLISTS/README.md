# `.gcc/CHECKLISTS/` — Governance & OS Checklists

> **Document type:** AI Operating System (V0-P4)
> **Status:** Authoritative checklists
> **Owner:** Founder · **Parent:** [`../README.md`](../README.md)
> **Update procedure:** Checklist changes are governance-class (ADR) — they encode gating criteria.

Actionable, copy-and-tick checklists that turn the governance framework
([`../../docs/governance/`](../../docs/governance/)) into **repeatable gates**. A
checklist item that cannot be ticked **blocks** the action (it is stop-and-remediate,
not advisory).

| Checklist | Use before | Framework |
|-----------|-----------|-----------|
| [`architecture_change_checklist.md`](./architecture_change_checklist.md) | Approving/merging an architecture-class change | [`Architecture_Governance.md`](../../docs/governance/Architecture_Governance.md) §12 |
| [`review_checklist.md`](./review_checklist.md) | Approving any change | [`Review_Governance.md`](../../docs/governance/Review_Governance.md) |
| [`ai_review_checklist.md`](./ai_review_checklist.md) | Approving AI-generated changes | [`AI_Governance.md`](../../docs/governance/AI_Governance.md) §8, [`Review_Governance.md`](../../docs/governance/Review_Governance.md) §8 |
| [`release_checklist.md`](./release_checklist.md) | Cutting a release / version tag | [`Release_Governance.md`](../../docs/governance/Release_Governance.md) |
| [`version_gate_checklist.md`](./version_gate_checklist.md) | Claiming a version's exit criteria | [`VERSION_STATUS.md`](../VERSION_STATUS.md), NR-12 |
| [`context_recovery_checklist.md`](./context_recovery_checklist.md) | Starting work after a context gap | [`CONTEXT_RECOVERY_PROTOCOL.md`](../CONTEXT_RECOVERY_PROTOCOL.md) |
| [`ai_onboarding_checklist.md`](./ai_onboarding_checklist.md) | A new AI agent's first contribution | [`AI_ONBOARDING_PROTOCOL.md`](../AI_ONBOARDING_PROTOCOL.md) |

**Convention:** every `[ ]` must become `[x]` (or be explicitly N/A with a reason)
before the gated action proceeds.
