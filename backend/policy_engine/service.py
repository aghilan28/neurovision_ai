"""PolicyService — the governed orchestration hub for the Policy & Constraint Engine.

Ties identity, taxonomy, lifecycle, constraints, deterministic evaluation,
governance, registry, audit, and lineage into the use cases that author policies and
constraints, move policies through their lifecycle, and evaluate requests. Every
mutation is: governance-gated -> audited (immutable) -> lineage-extended ->
version-bumped -> registry-synced.

Policies are the platform's **safety system**: explainable, deterministic, never
hidden. A policy only evaluates while ACTIVE and never becomes ACTIVE without
governance approval. Shares the platform's single ``ml.lineage.LineageTracker`` and
the shared ``ImmutableAuditLog`` — no parallel lineage/audit/governance.
"""

from __future__ import annotations

from typing import Optional, Sequence

from ml.lineage import LineageTracker  # allowed: backend -> ml

from .version import DETERMINISTIC_EPOCH
from .identity import mint_policy
from .policies.taxonomy import validate_policy_category, PolicyLifecycleState
from .policies.lifecycle import PolicyLifecycle
from .constraints import ConstraintEngine
from .evaluation import PolicyEvaluationEngine
from .governance import PolicyGovernanceGate, PolicyGovernanceError
from .registry import PolicyRegistry
from .validation import PolicyValidator
from .audit import make_policy_audit_log
from .lineage import make_policy_lineage, make_constraint_lineage, make_evaluation_lineage
from .models.domain import (
    PolicyRule, ConstraintRecord, PolicyRecord, PolicyEvaluation, PolicyVersion,
    PolicyRegistryRecord,
)
from .reports import (
    build_policy_summary_report, build_policy_registry_report, build_constraint_report,
    build_evaluation_report, build_policy_governance_report, build_policy_validation_report,
    build_policy_audit_report, build_policy_lineage_report,
)



class PolicyService:
    """Stateful service: policy registry, shared lineage tracker, immutable audit log."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[PolicyRegistry] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or PolicyRegistry()
        self.audit = make_policy_audit_log()
        self.lifecycle = PolicyLifecycle()
        self.gate = PolicyGovernanceGate()
        self.validator = PolicyValidator()
        self.constraints = ConstraintEngine()
        self.evaluator = PolicyEvaluationEngine()
        # live PolicyRecord aggregates (the registry holds version summaries; this
        # keeps the evaluable policy objects so the engine can re-evaluate requests).
        self.policy_cache: dict[str, PolicyRecord] = {}

    # --- constraints ----------------------------------------------------------
    def create_constraint(self, *, constraint_type: str, category: str, subject_kind: str,
                          constraint_key: str, rules: Sequence[PolicyRule] = (),
                          explanation: str = "", parents: Sequence[str] = (),
                          created_at: str = DETERMINISTIC_EPOCH) -> ConstraintRecord:
        """Build + register an explicit, versioned constraint (lineage-tracked)."""
        constraint = self.constraints.build(
            constraint_type=constraint_type, category=category, subject_kind=subject_kind,
            constraint_key=constraint_key, rules=rules, explanation=explanation)
        node = self.lineage.record(make_constraint_lineage(
            constraint.constraint_id, parents=parents, created_at=created_at))
        self.audit.append("constraint_created",
                          {"constraint_id": constraint.constraint_id,
                           "constraint_type": constraint_type, "lineage_id": node.lineage_id},
                          created_at=created_at)
        self.registry.register_constraint(constraint)
        self.audit.append("constraint_registered",
                          {"constraint_id": constraint.constraint_id,
                           "version": constraint.version}, created_at=created_at)
        return constraint

    # --- create policy --------------------------------------------------------
    def create_policy(self, *, category: str, policy_key: str, title: str, description: str,
                      subject_kind: str, rules: Sequence[PolicyRule] = (),
                      constraint_ids: Sequence[str] = (), derived_from: Sequence[str] = (),
                      owner: str = "policy-ops",
                      created_at: str = DETERMINISTIC_EPOCH) -> PolicyRecord:
        """Create a DRAFT policy, governance-gated + lineage-rooted."""
        validate_policy_category(category)
        for cid in constraint_ids:
            if not self.registry.has_constraint(cid):
                raise ValueError(f"unknown constraint {cid!r} (create it first)")
        ident = mint_policy(category, policy_key)
        policy = PolicyRecord(
            policy_id=ident.id, category=category, policy_key=policy_key, title=title,
            description=description, subject_kind=subject_kind, rules=tuple(rules),
            constraint_ids=tuple(constraint_ids), state=PolicyLifecycleState.DRAFT.value,
            owner=owner, created_at=created_at)

        parents = list(derived_from)
        report = self.gate.evaluate(policy=policy, parents=tuple(parents),
                                    requires_lineage=len(parents) > 0)
        self.gate.raise_if_failed(report)

        node = self.lineage.record(make_policy_lineage(
            policy.policy_id, parents=parents, reason="created", created_at=created_at))
        self.audit.append("policy_created",
                          {"policy_id": policy.policy_id, "category": category,
                           "lineage_id": node.lineage_id, "n_parents": len(parents)},
                          created_at=created_at)
        policy.lineage_id = node.lineage_id
        self._finalize(policy, reason="created", created_at=created_at)
        return policy



    # --- lifecycle transition (governed) -------------------------------------
    def transition(self, policy: PolicyRecord, target: PolicyLifecycleState, *,
                   reason: str = "", approved: bool = False, authority: Optional[str] = None,
                   created_at: str = DETERMINISTIC_EPOCH) -> PolicyRecord:
        """Move a policy to ``target`` (validated, governed, audited, versioned).

        APPROVED/ACTIVE require governance approval (``approved=True``); ACTIVE
        additionally fails the gate unless approved.
        """
        record = self.lifecycle.transition(PolicyLifecycleState(policy.state), target,
                                            reason=reason, created_at=created_at)
        if self.lifecycle.requires_governance(target):
            decision = "approved" if approved else "denied"
            self.audit.append("policy_governance_decision",
                              {"policy_id": policy.policy_id, "target": target.value,
                               "decision": decision, "authority": authority},
                              created_at=created_at)
            if not approved:
                policy.approval_state = "rejected"
                policy.approval_history = policy.approval_history + (
                    {"target": target.value, "decision": decision, "authority": authority,
                     "created_at": created_at},)
                self._finalize(policy, reason=f"governance_denied:{target.value}",
                               created_at=created_at)
                raise PolicyGovernanceError(
                    f"policy transition {policy.state}->{target.value} denied (not approved)")
            policy.approval_state = "approved"
            policy.approval_history = policy.approval_history + (
                {"target": target.value, "decision": decision, "authority": authority,
                 "created_at": created_at},)

        gate = self.gate.evaluate(
            policy=policy, parents=(policy.lineage_id,), requires_lineage=True,
            target_state=target, activation_approved=(policy.approval_state == "approved"))
        self.gate.raise_if_failed(gate)

        self.audit.append("policy_state_change", record.to_dict(), created_at=created_at)
        node = self.lineage.record(make_policy_lineage(
            policy.policy_id, parents=(policy.lineage_id,),
            reason=f"{record.from_state}->{record.to_state}", created_at=created_at,
            extra={"transition": record.to_dict()}))
        policy.state = target.value
        policy.lineage_id = node.lineage_id
        self._finalize(policy, reason=f"transition:{record.from_state}->{record.to_state}",
                       created_at=created_at)
        return policy

    def activate(self, policy: PolicyRecord, *, authority: str = "governance",
                 created_at: str = DETERMINISTIC_EPOCH) -> PolicyRecord:
        """Convenience: drive a DRAFT policy to ACTIVE through the governed path."""
        self.transition(policy, PolicyLifecycleState.UNDER_REVIEW, reason="submit",
                        created_at=created_at)
        self.transition(policy, PolicyLifecycleState.APPROVED, reason="approve", approved=True,
                        authority=authority, created_at=created_at)
        self.transition(policy, PolicyLifecycleState.ACTIVE, reason="activate", approved=True,
                        authority=authority, created_at=created_at)
        return policy

    # --- evaluation -----------------------------------------------------------
    def evaluate(self, policy: PolicyRecord, *, subject_kind: str, subject_id: str,
                 request: str, context: dict, subject_lineage_id: Optional[str] = None,
                 created_at: str = DETERMINISTIC_EPOCH) -> PolicyEvaluation:
        """Deterministically evaluate a request against an ACTIVE policy (explainable)."""
        if not policy.is_active:
            raise PolicyGovernanceError(
                f"policy {policy.policy_id} is not ACTIVE (state={policy.state}); "
                "only active policies may evaluate")
        constraints = self.registry.constraints_for(policy)
        evaluation = self.evaluator.evaluate(
            policy=policy, constraints=constraints, subject_kind=subject_kind,
            subject_id=subject_id, request=request, context=context)
        parents = [policy.lineage_id] + ([subject_lineage_id] if subject_lineage_id else [])
        node = self.lineage.record(make_evaluation_lineage(
            evaluation.evaluation_id, parents=parents, outcome=evaluation.outcome,
            created_at=created_at))
        self.audit.append("policy_evaluated",
                          {"evaluation_id": evaluation.evaluation_id,
                           "policy_id": policy.policy_id, "outcome": evaluation.outcome,
                           "lineage_id": node.lineage_id}, created_at=created_at)
        from dataclasses import replace
        evaluation = replace(evaluation, lineage_id=node.lineage_id, audit_state=self.audit.head)
        self.registry.register_evaluation(evaluation)
        return evaluation

    # --- validation + reports -------------------------------------------------
    def validate(self, policy: PolicyRecord):
        return self.validator.validate(policy=policy, registry=self.registry,
                                       audit_log=self.audit, lineage_tracker=self.lineage)

    def reports(self, policies: Sequence) -> dict:
        policies = list(policies)
        return {
            "policy_summary_report": build_policy_summary_report(policies),
            "policy_registry_report": build_policy_registry_report(self.registry),
            "constraint_report": build_constraint_report(self.registry),
            "evaluation_report": build_evaluation_report(self.registry),
            "policy_governance_report": build_policy_governance_report(policies),
            "policy_audit_report": build_policy_audit_report(self.audit),
            "policy_lineage_report": build_policy_lineage_report(policies, self.lineage),
        }

    def validation_report(self, scope: str, validation_report_dict: dict) -> dict:
        return build_policy_validation_report(scope, validation_report_dict)

    # --- internals ------------------------------------------------------------
    def _finalize(self, policy: PolicyRecord, *, reason: str, created_at: str) -> None:
        previous = policy.version or None
        new_version = PolicyVersion.compute(policy.state_signature(), previous)
        policy.previous_version = previous
        policy.version = new_version
        self.audit.append("policy_version_changed",
                          {"policy_id": policy.policy_id, "version": new_version,
                           "reason": reason}, created_at=created_at)
        policy.audit_state = self.audit.head
        self.registry.register(PolicyRegistryRecord(
            policy_id=policy.policy_id, category=policy.category, subject_kind=policy.subject_kind,
            state=policy.state, approval_state=policy.approval_state, version=new_version,
            constraint_ids=policy.constraint_ids, lineage_id=policy.lineage_id,
            audit_state=policy.audit_state, content_signature_value=policy.state_signature()))
        self.audit.append("policy_registered",
                          {"policy_id": policy.policy_id, "version": new_version},
                          created_at=created_at)
        policy.audit_state = self.audit.head
        self.policy_cache[policy.policy_id] = policy
