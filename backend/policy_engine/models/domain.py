"""Policy & constraint domain entities (V4-P2).

Pure data + ``to_dict`` + (where relevant) ``state_signature``. Policies are the
platform's **safety system**: they make explicit what is ALLOWED / FORBIDDEN /
REQUIRED / ESCALATED. Every policy and constraint is deterministic and
**explainable** — no hidden logic; an evaluation always records exactly which rules
and constraints fired and why.

Mandated entities: ``PolicyIdentity`` (in ``identity``), ``PolicyRecord``,
``PolicyRule``, ``PolicyEvaluation``, ``ConstraintRecord``, ``ConstraintCategory``
(in ``policies.taxonomy``), ``PolicyVersion``, ``PolicyAuditRecord``,
``PolicyLineageRecord``, ``PolicyRegistryRecord``.

A ``PolicyRule`` is a transparent, declarative predicate over an evaluation
**context** (a flat mapping of facts). It compares a context fact against an
expected value with a small, fixed set of operators — there is no executable code
in a rule, so its behaviour is fully explainable and reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    POLICY_DOMAIN_VERSION, POLICY_RULE_VERSION, CONSTRAINT_VERSION,
    POLICY_EVALUATION_VERSION, POLICY_REGISTRY_VERSION, DETERMINISTIC_EPOCH,
)

# the fixed, transparent operator set a rule may use (no hidden logic).
_OPERATORS = frozenset({"eq", "ne", "in", "not_in", "exists", "not_exists", "ge", "le", "truthy"})


@dataclass(frozen=True)
class PolicyRule:
    """A transparent, declarative predicate over an evaluation context.

    ``fact`` is a key looked up in the context mapping; ``operator`` is one of the
    fixed set; ``value`` is the comparison operand. ``negate`` flips the result.
    ``description`` makes the rule self-explaining. A rule has **no executable
    code** — it is data, so its outcome is deterministic and fully explainable.
    """

    rule_id: str
    fact: str
    operator: str
    value: Any = None
    negate: bool = False
    description: str = ""
    rule_version: str = POLICY_RULE_VERSION

    def evaluate(self, context: dict) -> tuple[bool, str]:
        """Return (passed, explanation) — deterministic, side-effect free."""
        if self.operator not in _OPERATORS:
            return False, f"unknown operator {self.operator!r}"
        present = self.fact in context
        actual = context.get(self.fact)
        op = self.operator
        if op == "exists":
            result = present
        elif op == "not_exists":
            result = not present
        elif op == "truthy":
            result = bool(actual)
        elif op == "eq":
            result = actual == self.value
        elif op == "ne":
            result = actual != self.value
        elif op == "in":
            result = actual in (self.value or [])
        elif op == "not_in":
            result = actual not in (self.value or [])
        elif op == "ge":
            result = present and actual is not None and actual >= self.value
        elif op == "le":
            result = present and actual is not None and actual <= self.value
        else:  # pragma: no cover - guarded above
            result = False
        if self.negate:
            result = not result
        explanation = (f"{self.fact} {op} {self.value!r}"
                       f"{' (negated)' if self.negate else ''} -> {result} "
                       f"[actual={actual!r}]")
        return bool(result), explanation

    def state_signature(self) -> str:
        return hash_obj({"rule_id": self.rule_id, "fact": self.fact, "operator": self.operator,
                         "value": self.value, "negate": self.negate})

    def to_dict(self) -> dict:
        return {"rule_id": self.rule_id, "fact": self.fact, "operator": self.operator,
                "value": self.value, "negate": self.negate, "description": self.description,
                "rule_version": self.rule_version}


@dataclass(frozen=True)
class ConstraintRecord:
    """An explicit, versioned, explainable constraint.

    ``constraint_type`` is one of ALLOWED/FORBIDDEN/REQUIRED/ESCALATED/DEFERRED/
    CONDITIONAL. ``subject_kind`` is the artifact kind it governs (goal, plan,
    finding, workflow, ...). ``rules`` are the predicates that decide whether the
    constraint *applies* to a given context. ``explanation`` documents intent.
    """

    constraint_id: str
    constraint_type: str
    category: str
    subject_kind: str
    constraint_key: str
    rules: tuple[PolicyRule, ...] = ()
    explanation: str = ""
    version: str = ""
    constraint_version: str = CONSTRAINT_VERSION

    def applies(self, context: dict) -> tuple[bool, list]:
        """Whether every rule passes for this context (the constraint is triggered)."""
        explanations = []
        ok = True
        for rule in self.rules:
            passed, why = rule.evaluate(context)
            explanations.append({"rule_id": rule.rule_id, "passed": passed, "why": why})
            ok = ok and passed
        # a constraint with no rules always applies (an unconditional constraint)
        return (ok if self.rules else True), explanations

    def state_signature(self) -> str:
        return hash_obj({"constraint_id": self.constraint_id,
                         "constraint_type": self.constraint_type, "category": self.category,
                         "subject_kind": self.subject_kind, "constraint_key": self.constraint_key,
                         "rules": [r.state_signature() for r in self.rules]})

    def to_dict(self) -> dict:
        return {"constraint_id": self.constraint_id, "constraint_type": self.constraint_type,
                "category": self.category, "subject_kind": self.subject_kind,
                "constraint_key": self.constraint_key,
                "rules": [r.to_dict() for r in self.rules], "explanation": self.explanation,
                "version": self.version, "constraint_version": self.constraint_version,
                "state_signature": self.state_signature()}



@dataclass
class PolicyRecord:
    """A first-class, governed, explainable policy.

    A policy belongs to one category (permission/prohibition/obligation/escalation/
    risk/governance/quality/workflow), governs a ``subject_kind`` (e.g. goal), binds
    a set of :class:`ConstraintRecord`, and carries an applicability predicate
    (``rules``). It only evaluates requests while ACTIVE, and never becomes ACTIVE
    without governance approval. Mutable aggregate (lifecycle evolves) — all
    mutation flows through the service's governed path.
    """

    policy_id: str
    category: str
    policy_key: str
    title: str
    description: str
    subject_kind: str
    rules: tuple[PolicyRule, ...] = ()           # when the policy applies
    constraint_ids: tuple[str, ...] = ()         # constraints this policy enforces
    state: str = "draft"
    approval_state: str = "pending"
    approval_history: tuple[dict, ...] = ()
    version: str = ""
    previous_version: Optional[str] = None
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    owner: str = "policy-ops"
    created_at: str = DETERMINISTIC_EPOCH
    domain_version: str = POLICY_DOMAIN_VERSION

    @property
    def is_active(self) -> bool:
        return self.state == "active"

    def applies(self, context: dict) -> tuple[bool, list]:
        explanations = []
        ok = True
        for rule in self.rules:
            passed, why = rule.evaluate(context)
            explanations.append({"rule_id": rule.rule_id, "passed": passed, "why": why})
            ok = ok and passed
        return (ok if self.rules else True), explanations

    def state_signature(self) -> str:
        return hash_obj({"policy_id": self.policy_id, "category": self.category,
                         "policy_key": self.policy_key, "title": self.title,
                         "description": self.description, "subject_kind": self.subject_kind,
                         "rules": [r.state_signature() for r in self.rules],
                         "constraint_ids": list(self.constraint_ids), "state": self.state,
                         "approval_state": self.approval_state,
                         "approval_history": list(self.approval_history)})

    def to_dict(self) -> dict:
        return {"policy_id": self.policy_id, "category": self.category,
                "policy_key": self.policy_key, "title": self.title,
                "description": self.description, "subject_kind": self.subject_kind,
                "rules": [r.to_dict() for r in self.rules],
                "constraint_ids": list(self.constraint_ids), "state": self.state,
                "approval_state": self.approval_state,
                "approval_history": list(self.approval_history), "version": self.version,
                "lineage_id": self.lineage_id, "audit_state": self.audit_state,
                "owner": self.owner, "created_at": self.created_at,
                "domain_version": self.domain_version, "state_signature": self.state_signature()}


@dataclass(frozen=True)
class PolicyEvaluation:
    """A deterministic, explainable record of a single policy evaluation.

    Captures the evaluation context, which policy was applied, which constraints
    triggered, the decision outcome, and the supporting evidence (per-rule
    explanations) — so every decision is fully reconstructable. No hidden logic.
    """

    evaluation_id: str
    policy_id: str
    subject_kind: str
    subject_id: str
    request: str                                 # the action/decision being evaluated
    outcome: str                                 # an EvaluationOutcome value
    context: dict = field(default_factory=dict)
    applied_rules: tuple[dict, ...] = ()
    triggered_constraints: tuple[dict, ...] = ()
    evidence: tuple[str, ...] = ()
    lineage_id: Optional[str] = None
    audit_state: Optional[str] = None
    evaluation_version: str = POLICY_EVALUATION_VERSION

    def request_signature(self) -> str:
        return hash_obj({"policy_id": self.policy_id, "subject_kind": self.subject_kind,
                         "subject_id": self.subject_id, "request": self.request,
                         "context": self.context})

    def state_signature(self) -> str:
        return hash_obj({"evaluation_id": self.evaluation_id, "policy_id": self.policy_id,
                         "subject_id": self.subject_id, "request": self.request,
                         "outcome": self.outcome, "context": self.context,
                         "applied_rules": list(self.applied_rules),
                         "triggered_constraints": list(self.triggered_constraints)})

    def to_dict(self) -> dict:
        return {"evaluation_id": self.evaluation_id, "policy_id": self.policy_id,
                "subject_kind": self.subject_kind, "subject_id": self.subject_id,
                "request": self.request, "outcome": self.outcome, "context": self.context,
                "applied_rules": list(self.applied_rules),
                "triggered_constraints": list(self.triggered_constraints),
                "evidence": list(self.evidence), "lineage_id": self.lineage_id,
                "audit_state": self.audit_state, "evaluation_version": self.evaluation_version,
                "state_signature": self.state_signature()}


# --- version / audit / lineage / registry projections ------------------------
@dataclass(frozen=True)
class PolicyVersion:
    version: str
    previous: Optional[str]
    reason: str
    created_at: str = DETERMINISTIC_EPOCH

    @staticmethod
    def compute(state_signature: str, previous: Optional[str]) -> str:
        return hash_obj({"state": state_signature, "previous": previous})

    def to_dict(self) -> dict:
        return {"version": self.version, "previous": self.previous, "reason": self.reason,
                "created_at": self.created_at}


@dataclass(frozen=True)
class PolicyAuditRecord:
    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {"seq": self.seq, "kind": self.kind, "payload": self.payload,
                "prev_hash": self.prev_hash, "event_hash": self.event_hash,
                "created_at": self.created_at}


@dataclass(frozen=True)
class PolicyLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


@dataclass
class PolicyRegistryRecord:
    policy_id: str
    category: str
    subject_kind: str
    state: str
    approval_state: str
    version: str
    constraint_ids: tuple[str, ...]
    lineage_id: str
    audit_state: str
    content_signature_value: str
    policy_registry_version: str = POLICY_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"policy_id": self.policy_id, "category": self.category,
                         "state": self.state, "approval_state": self.approval_state,
                         "version": self.version, "lineage_id": self.lineage_id,
                         "content": self.content_signature_value})

    def to_dict(self) -> dict:
        return {"policy_id": self.policy_id, "category": self.category,
                "subject_kind": self.subject_kind, "state": self.state,
                "approval_state": self.approval_state, "version": self.version,
                "constraint_ids": list(self.constraint_ids), "lineage_id": self.lineage_id,
                "audit_state": self.audit_state,
                "content_signature_value": self.content_signature_value,
                "policy_registry_version": self.policy_registry_version,
                "content_signature": self.content_signature()}
