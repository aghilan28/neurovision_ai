"""Policy evaluation engine (V4-P2).

Deterministically evaluates a policy (with its bound constraints) against an
evaluation **context** and produces one explainable :class:`PolicyEvaluation` whose
outcome is one of:

    PERMITTED | DENIED | REQUIRES_REVIEW | ESCALATED | CONDITIONAL_APPROVAL

The decision procedure is a fixed, transparent precedence over the constraint types
that *apply* in the context (no hidden logic). Precedence (highest first):

    FORBIDDEN  -> DENIED
    REQUIRED (unmet)        -> DENIED
    ESCALATED  -> ESCALATED
    DEFERRED   -> REQUIRES_REVIEW
    CONDITIONAL -> CONDITIONAL_APPROVAL
    (otherwise / ALLOWED)   -> PERMITTED

Every applied rule and triggered constraint is recorded with its explanation, so
the decision is fully reconstructable and reproducible.
"""

from __future__ import annotations

from typing import Sequence

from ..identity import mint_evaluation
from ..policies.taxonomy import ConstraintType, EvaluationOutcome
from ..models.domain import PolicyRecord, ConstraintRecord, PolicyEvaluation


class PolicyEvaluationEngine:
    """Deterministic, explainable policy evaluator."""

    def evaluate(self, *, policy: PolicyRecord, constraints: Sequence[ConstraintRecord],
                 subject_kind: str, subject_id: str, request: str,
                 context: dict) -> PolicyEvaluation:
        context = dict(context)

        # 1. does the policy apply at all?
        applies, applied_rules = policy.applies(context)

        # 2. which bound constraints are triggered in this context?
        triggered: list[dict] = []
        evidence: list[str] = []
        types_triggered: set[str] = set()
        for c in constraints:
            c_applies, why = c.applies(context)
            if c_applies:
                triggered.append({"constraint_id": c.constraint_id,
                                  "constraint_type": c.constraint_type,
                                  "category": c.category, "rules": why})
                types_triggered.add(c.constraint_type)
                evidence.append(f"constraint {c.constraint_id} ({c.constraint_type}) applies")

        # 3. deterministic precedence over triggered constraint types
        if not applies:
            outcome = EvaluationOutcome.PERMITTED.value
            evidence.append("policy does not apply to this context -> permitted (no constraint)")
        elif ConstraintType.FORBIDDEN.value in types_triggered:
            outcome = EvaluationOutcome.DENIED.value
            evidence.append("a FORBIDDEN constraint is triggered -> denied")
        elif ConstraintType.REQUIRED.value in types_triggered \
                and not self._required_met(constraints, context):
            outcome = EvaluationOutcome.DENIED.value
            evidence.append("a REQUIRED constraint is unmet -> denied")
        elif ConstraintType.ESCALATED.value in types_triggered:
            outcome = EvaluationOutcome.ESCALATED.value
            evidence.append("an ESCALATED constraint is triggered -> escalated")
        elif ConstraintType.DEFERRED.value in types_triggered:
            outcome = EvaluationOutcome.REQUIRES_REVIEW.value
            evidence.append("a DEFERRED constraint is triggered -> requires review")
        elif ConstraintType.CONDITIONAL.value in types_triggered:
            outcome = EvaluationOutcome.CONDITIONAL_APPROVAL.value
            evidence.append("a CONDITIONAL constraint is triggered -> conditional approval")
        else:
            outcome = EvaluationOutcome.PERMITTED.value
            evidence.append("policy applies; only ALLOWED/no blocking constraints -> permitted")

        eval_id = mint_evaluation(policy.policy_id, hashable_request(
            policy.policy_id, subject_kind, subject_id, request, context))
        return PolicyEvaluation(
            evaluation_id=eval_id, policy_id=policy.policy_id, subject_kind=subject_kind,
            subject_id=subject_id, request=request, outcome=outcome, context=context,
            applied_rules=tuple(applied_rules), triggered_constraints=tuple(triggered),
            evidence=tuple(evidence))

    @staticmethod
    def _required_met(constraints: Sequence[ConstraintRecord], context: dict) -> bool:
        """A REQUIRED constraint is met iff its `requirement_met` fact is truthy.

        The fact name is the constraint's ``constraint_key`` suffixed with
        ``_satisfied`` (transparent convention), or a generic ``requirement_met``.
        """
        for c in constraints:
            if c.constraint_type != ConstraintType.REQUIRED.value:
                continue
            applies, _ = c.applies(context)
            if not applies:
                continue
            key = f"{c.constraint_key}_satisfied"
            met = bool(context.get(key, context.get("requirement_met", False)))
            if not met:
                return False
        return True


def hashable_request(policy_id: str, subject_kind: str, subject_id: str, request: str,
                     context: dict) -> str:
    from ml.provenance import hash_obj  # allowed: backend -> ml
    return hash_obj({"policy_id": policy_id, "subject_kind": subject_kind,
                     "subject_id": subject_id, "request": request, "context": context})
