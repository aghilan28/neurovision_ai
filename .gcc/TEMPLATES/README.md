# `.gcc/TEMPLATES/` — Governance & OS Templates

> **Document type:** AI Operating System (V0-P4)
> **Status:** Authoritative templates
> **Owner:** Founder · **Parent:** [`../README.md`](../README.md)
> **Update procedure:** Template changes are governance-class (ADR) — templates encode required fields, so changing them changes the process.

Reusable, fillable templates that make the governance framework
([`../../docs/governance/`](../../docs/governance/)) and the operating system
**easy to follow correctly**. Copy a template, fill every field, and link it from
the relevant registry/changelog. **Every field is required unless marked
optional** — a record missing a mandatory field is not valid.

| Template | Use for | Framework | Lands in |
|----------|---------|-----------|----------|
| [`ADR_TEMPLATE.md`](./ADR_TEMPLATE.md) | Recording a decision | [`Decision_Governance.md`](../../docs/governance/Decision_Governance.md) | `.gcc/decisions/` + [`DECISION_REGISTRY.md`](../DECISION_REGISTRY.md) |
| [`RFC_TEMPLATE.md`](./RFC_TEMPLATE.md) | Proposing a non-trivial change | [`RFC_Process.md`](../../docs/governance/RFC_Process.md) | `.gcc/rfcs/` |
| [`RISK_TEMPLATE.md`](./RISK_TEMPLATE.md) | Registering a risk | [`Risk_Governance.md`](../../docs/governance/Risk_Governance.md) | [`ACTIVE_RISKS.md`](../ACTIVE_RISKS.md) |
| [`ASSUMPTION_TEMPLATE.md`](./ASSUMPTION_TEMPLATE.md) | Recording an assumption | Risk/Lore | [`ACTIVE_ASSUMPTIONS.md`](../ACTIVE_ASSUMPTIONS.md) |
| [`CHANGE_RECORD_TEMPLATE.md`](./CHANGE_RECORD_TEMPLATE.md) | Logging a change | [`Change_Management.md`](../../docs/governance/Change_Management.md) | [`CHANGELOG_SYSTEM.md`](../CHANGELOG_SYSTEM.md) / `CHANGELOG.md` |
| [`POSTMORTEM_TEMPLATE.md`](./POSTMORTEM_TEMPLATE.md) | After an incident/failure | [`Release_Governance.md`](../../docs/governance/Release_Governance.md) §8 | `.gcc/postmortems/` |
| [`LEARNING_TEMPLATE.md`](./LEARNING_TEMPLATE.md) | Capturing a learning | [`LORE_PROTOCOL.md`](../LORE_PROTOCOL.md) §6 | `.gcc/learnings/` |
| [`COMMIT_MESSAGE_TEMPLATE.md`](./COMMIT_MESSAGE_TEMPLATE.md) | Annotating commits | [`LORE_PROTOCOL.md`](../LORE_PROTOCOL.md) §5 | git |
| [`ai_prompt_template.md`](./ai_prompt_template.md) | Constructing a compliant AI prompt | [`AI_Governance.md`](../../docs/governance/AI_Governance.md) §3 | the prompt |

Convention: IDs are monotonic and zero-padded (`ADR-0007`, `RFC-0003`, `RISK-0012`,
`ASM-0004`, `DEP-0002`). Records are **append-only**; superseded items are marked,
never deleted (NR-14).
