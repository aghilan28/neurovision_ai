# V4 Audit Framework

> Procedures, checklists, evidence requirements, escalation rules, a severity model,
> and remediation/closure models for auditing Version 4.

## 1. Audit procedures

| Step | Procedure | Tooling |
|------|-----------|---------|
| A1 | Inventory every V4 subsystem + its public surface | repository scan |
| A2 | Execute the full test suite | `pytest` |
| A3 | Execute every `verify_v4_p*` script | `python -m scripts.verify_v4_p*` |
| A4 | Verify lineage reaches the patient from each subsystem | runtime `verify_chain` |
| A5 | Verify every audit log chain is intact | runtime `audit.verify()` |
| A6 | Confirm determinism (repeat builds → identical ids) | runtime |
| A7 | Confirm boundaries (frontend imports no domain; lint clean) | `pytest` + `ruff` |
| A8 | Confirm governance gates admit valid / reject invalid | runtime |
| A9 | Record findings, classify severity, assign remediation | this framework |

## 2. Audit checklists

**Per backend subsystem:** identity ▢ models ▢ governance gate ▢ registry ▢ validation
▢ audit ▢ lineage ▢ reports ▢ schemas ▢ service ▢ tests ▢ docs ▢.

**Per artifact:** versioned ▢ traceable ▢ auditable ▢ lineage-tracked ▢ governed ▢
deterministic ▢ explainable ▢.

**Cross-cutting:** shared lineage tracker (no parallel) ▢ shared audit log (no parallel)
▢ no boundary violation ▢ no forbidden work ▢.

## 3. Audit evidence requirements

Every finding must cite reproducible evidence: a test name, a verify-script criterion,
or a runtime assertion (lineage/audit/determinism). Assertion-free findings are invalid.

## 4. Severity model

| Severity | Definition | Example |
|----------|------------|---------|
| **Critical** | violates a non-negotiable safety/governance invariant | a subsystem bypasses policy/approval; audit chain not verifiable; simulation executes |
| **High** | breaks traceability/determinism or a phase boundary | lineage does not reach patient; non-deterministic build; frontend imports domain |
| **Moderate** | incomplete artifact/report/validation without safety impact | a report missing; a validation dimension absent |
| **Low** | cosmetic / documentation | wording, lint debt in non-V4 legacy code |

## 5. Escalation rules

- **Critical** → block certification immediately; halt; require remediation + re-audit.
- **High** → block certification; remediation required before grade ≥ CONDITIONAL.
- **Moderate** → allowed under CONDITIONAL only with a documented remediation plan.
- **Low** → tracked; never blocks.

## 6. Remediation model

Each finding → owner subsystem, remediation action, evidence to re-collect, and a
re-audit step (A2–A8). Remediation is complete only when the re-collected evidence
passes.

## 7. Closure model

A finding is **closed** when its re-collected evidence passes and the change is
additive (no regression in the full suite). The audit is **closed** when no Critical or
High finding is open and `scripts/verify_v4_p9_p10.py` returns `ALL CRITERIA PASS`.
