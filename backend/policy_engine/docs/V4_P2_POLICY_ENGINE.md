# V4-P2 — Policy & Constraint Engine (design notes)

> **Phase:** V4-P2 · **Subsystem:** `backend/policy_engine/` · **ADR:** ADR-0011

## Purpose
Make the platform's **boundaries** explicit and enforceable: ALLOWED / FORBIDDEN /
REQUIRED / ESCALATED. Policies are the safety system that must exist *before* any
planning or execution. Everything is deterministic and explainable.

## Why "no hidden logic"
A `PolicyRule` is declarative data — a fact key, a fixed operator, an operand, an
optional negate — evaluated against a flat context mapping. There is no executable
code in a rule or constraint, so a policy's behaviour is fully reconstructable from
its data, and an evaluation can record a precise per-rule explanation.

## Constraints (six types)
ALLOWED / FORBIDDEN / REQUIRED / ESCALATED / DEFERRED / CONDITIONAL. Each is a
versioned, content-addressed record with applicability rules. A constraint *applies*
when all its rules pass (a ruleless constraint is unconditional). `FORBIDDEN` denies;
an unmet `REQUIRED` (its `<key>_satisfied` / `requirement_met` fact is falsey)
denies.

## Evaluation (five outcomes, fixed precedence)
`FORBIDDEN → DENIED`; `REQUIRED unmet → DENIED`; `ESCALATED → ESCALATED`;
`DEFERRED → REQUIRES_REVIEW`; `CONDITIONAL → CONDITIONAL_APPROVAL`; otherwise
`PERMITTED`. The evaluation id is `policyeval+hash(policy_id, request, context)`, so
the same request reproduces the same explainable record.

## Lifecycle + governance
A policy evaluates only while ACTIVE, and reaches ACTIVE only through
draft → under_review → approved → active, each governed transition requiring
approval (the gate's *governance* dimension fails an unapproved activation).

## Goal ↔ Policy integration
`install_default_goal_policies` creates one ACTIVE governance/obligation policy per
goal hook, each binding a REQUIRED constraint encoding the governance requirement.
`goal_policy_decider` builds a deterministic context from the goal, evaluates the
matching policy, and maps PERMITTED/CONDITIONAL_APPROVAL → approved. The decision is
audited and lineage-tracked: the evaluation node parents the policy node and the
goal node, so it traces to the patient.

## Traceability + determinism
Shares the single `ml.lineage.LineageTracker` and `ImmutableAuditLog`. No wall-clock;
ids/versions/audit heads are content-addressed; identical inputs reproduce identical
policies, constraints, and evaluations.

## Validation (eight dimensions)
policy · constraint · evaluation · registry · governance · audit · lineage · version.

## Scope guard (NR-13)
No planning, tasks, agents, execution, simulation, autonomous action, or V5 features.
Policies decide and explain; they never act.
