# Context Recovery Checklist

> **Framework:** [`../CONTEXT_RECOVERY_PROTOCOL.md`](../CONTEXT_RECOVERY_PROTOCOL.md)
> Use before any work session that follows a context gap (new agent/chat, returning
> after dormancy, or whenever unsure). Tick as you read; do not skip or reorder.

## Read (in order)
- [ ] 1. [`../MAIN_CONTEXT.md`](../MAIN_CONTEXT.md)
- [ ] 2. [`../CURRENT_STATE.md`](../CURRENT_STATE.md)
- [ ] 3. [`../NEXT_STATE.md`](../NEXT_STATE.md)
- [ ] 4. [`../VERSION_STATUS.md`](../VERSION_STATUS.md)
- [ ] 5. Constitution: VISION → OBJECTIVES → SCOPE
- [ ] 6. [`../../docs/VERSION_EVOLUTION_MODEL.md`](../../docs/VERSION_EVOLUTION_MODEL.md)
- [ ] 7. PRINCIPLES (AP) + NON_NEGOTIABLE_RULES (NR)
- [ ] 8. [`../../docs/GLOSSARY.md`](../../docs/GLOSSARY.md)
- [ ] 9. [`../../docs/architecture/`](../../docs/architecture/) (layered → system context → boundaries → graph → import rules)
- [ ] 10. [`../../docs/governance/README.md`](../../docs/governance/README.md) (+ task-relevant domain doc)
- [ ] 11. [`../DECISION_REGISTRY.md`](../DECISION_REGISTRY.md)
- [ ] 12. [`../ACTIVE_RISKS.md`](../ACTIVE_RISKS.md) + [`../ACTIVE_ASSUMPTIONS.md`](../ACTIVE_ASSUMPTIONS.md)
- [ ] 13. [`../DEPENDENCY_REGISTRY.md`](../DEPENDENCY_REGISTRY.md)
- [ ] 14. [`../KNOWLEDGE_GRAPH.md`](../KNOWLEDGE_GRAPH.md)
- [ ] 15. [`../LORE_PROTOCOL.md`](../LORE_PROTOCOL.md) + [`../CHANGELOG_SYSTEM.md`](../CHANGELOG_SYSTEM.md)
- [ ] 16. Task-local: the target module README + any ADR/RFC it links

## Validate understanding (answer all from the docs — no founder help)
- [ ] What NeuroVision AI is and is **not**.
- [ ] Current **version/phase** and the immediate next objective.
- [ ] **Five** rules and the principle each enforces.
- [ ] The **dependency direction** + one **forbidden import**.
- [ ] Why **patient-disjoint** validation is mandatory.
- [ ] What every **clinical output** must carry, and why.
- [ ] How to **propose** + **record** a consequential change.
- [ ] The **top open risk** and one **open assumption**.
- [ ] Where to **record why** you changed something.
- [ ] What governs the **specific module** you'll touch.

## After dormancy (extra)
- [ ] Re-ran documentation audit (Documentation_Governance §8).
- [ ] Re-ran architecture audit (Architecture_Governance §10).
- [ ] Re-reviewed Critical/High risks; re-validated open assumptions.

**Gate:** all validation answers correct ⇒ cleared to plan work. Any gap ⇒ re-read
the mapped source (or fix the doc gap) before proceeding — **never guess**.
