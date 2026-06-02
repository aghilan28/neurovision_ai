# Change Record — <type>(<scope>): <summary>

> **Framework:** [`../../docs/governance/Change_Management.md`](../../docs/governance/Change_Management.md) + [`../CHANGELOG_SYSTEM.md`](../CHANGELOG_SYSTEM.md)
> One record per change that merges to `main`. Paste into the changelog
> (`CHANGELOG.md` at repo root) at merge time.

```
## [<version-tag or YYYY-MM-DD>] — <type>(<scope>): <summary>
- Why:        <reason / problem solved>
- What:       <what changed>
- Class:      <A0|A1|A2|A3|AE>            (Architecture_Governance §13.1)
- Type:       <arch|gov|feat|fix|docs|test|refactor|chore|release|incident>
- Modules:    <modules touched; note explicit "did not touch">
- Refs:       <ADR-NNNN, RFC-NNNN, RISK-NNNN, DEP-NNNN as applicable>
- Invariants: <which checked / preserved>
- Validation: <tests + GCC result>
- Review:     <human reviewer — never the producing agent (NR-7)>
- Rollback:   <how to reverse, or link>
- AI-TRACE:   <present for AI-authored changes; see AI_Governance §9; else "n/a">
```

**Required for:** all Major/Architecture/Governance/Emergency changes; concise form
for Minor/Documentation. Entries are **append-only**; corrections are new entries
referencing the prior one.
