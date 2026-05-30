"""ExecutionService — the governed orchestration hub for the Execution Orchestration Layer.

Ties identity, lifecycle, coordination, monitoring, governance, registry, audit, and
lineage into the use cases that create an Execution (referencing an approved agent
assignment), authorize it, move it through its lifecycle, and observe it. Every
mutation is: governance-gated -> audited (immutable) -> lineage-extended ->
version-bumped -> registry-synced.

An **Execution** is the *governed progression of approved work* — never autonomous
action. The transition into ACTIVE requires **authorization** (a policy decision):
the service calls an injected ``policy_decider`` (the V4-P2 policy engine, wired by
the integration layer). If none is injected, governed transitions require an explicit
caller ``approved=True``. **Every execution must reference an approved agent
assignment** whose state is progressable; coordination references existing approved
artifacts and never plans new ones. Shares the platform's single
``ml.lineage.LineageTracker`` and the shared ``ImmutableAuditLog`` — no parallel
lineage/audit/governance.
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence

from ml.lineage import LineageTracker  # allowed: backend -> ml

from .version import DETERMINISTIC_EPOCH
from .identity import mint_execution, mint_relationship
from .lifecycle import ExecutionLifecycle, ExecutionLifecycleState
from .governance import ExecutionGovernanceGate, ExecutionGovernanceError
from .registry import ExecutionRegistry
from .validation import ExecutionValidator
from .audit import make_execution_audit_log
from .coordination import (
    context_complete, assignment_consistent, assignment_progressable, coordination_parents,
)
from .monitoring import observe
from .lineage import make_execution_lineage, make_relationship_lineage
from .models.domain import (
    ExecutionMetadata, ExecutionContext, ExecutionAssignment, ExecutionGovernanceRecord,
    ExecutionRelationship, ExecutionVersion, ExecutionRegistryRecord, ExecutionRecord,
)
from .reports import (
    build_execution_summary_report, build_authorization_report, build_status_report,
    build_monitoring_report, build_execution_governance_report, build_execution_validation_report,
    build_execution_audit_report, build_execution_lineage_report,
)

# A policy decider takes (hook, execution) and returns (approved, decision, policy_id, authority).
PolicyDecider = Callable[[str, ExecutionRecord], tuple]


class ExecutionCoordinationError(RuntimeError):
    """Raised when an execution references an incomplete/inconsistent/non-progressable context."""



class ExecutionService:
    """Stateful service: execution registry, shared lineage tracker, immutable audit log."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[ExecutionRegistry] = None,
                 policy_decider: Optional[PolicyDecider] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or ExecutionRegistry()
        self.audit = make_execution_audit_log()
        self.lifecycle = ExecutionLifecycle()
        self.gate = ExecutionGovernanceGate()
        self.validator = ExecutionValidator()
        self.policy_decider = policy_decider

    # --- create (reference an approved agent assignment) ---------------------
    def create_execution(self, *, execution_key: str, metadata: ExecutionMetadata,
                         context: ExecutionContext, assignment: ExecutionAssignment,
                         assignment_lineage_id: str, extra_parents: Sequence[str] = (),
                         owner: str = "execution-ops",
                         created_at: str = DETERMINISTIC_EPOCH) -> ExecutionRecord:
        """Create a PROPOSED execution that progresses an approved assignment.

        Every execution must reference an approved agent assignment whose state is
        progressable; the caller supplies the assignment's lineage node so the
        execution traces back through the assignment -> agent/task -> ... -> patient.
        """
        complete, missing = context_complete(context)
        if not complete:
            raise ExecutionCoordinationError(f"incomplete coordination context: missing {missing}")
        consistent, why = assignment_consistent(context, assignment)
        if not consistent:
            raise ExecutionCoordinationError(f"assignment inconsistent with context: {why}")
        if not assignment_progressable(assignment.assignment_state):
            raise ExecutionCoordinationError(
                f"assignment {assignment.assignment_id} state {assignment.assignment_state!r} "
                "is not progressable (must be 'assigned')")
        ident = mint_execution(context.task_id, assignment.assignment_id, execution_key)
        execution = ExecutionRecord(
            execution_id=ident.id, execution_key=execution_key, metadata=metadata,
            context=context, assignment=assignment, state=ExecutionLifecycleState.PROPOSED,
            governance=ExecutionGovernanceRecord(
                policy_references=context.policy_references,
                constraint_references=context.constraint_references),
            constraints=context.constraint_references, owner=owner, created_at=created_at)

        parents = list(coordination_parents(context, assignment_lineage_id)) + list(extra_parents)
        report = self.gate.evaluate(execution=execution, parents=tuple(parents),
                                    requires_lineage=True)
        self.gate.raise_if_failed(report)

        node = self.lineage.record(make_execution_lineage(
            execution.execution_id, parents=parents, reason="created", created_at=created_at))
        self.audit.append("execution_created",
                          {"execution_id": execution.execution_id, "task_id": context.task_id,
                           "assignment_id": assignment.assignment_id,
                           "lineage_id": node.lineage_id, "n_parents": len(parents)},
                          created_at=created_at)
        execution.lineage_id = node.lineage_id
        execution.status = observe(execution)
        self._finalize(execution, reason="created", created_at=created_at)
        return execution

    # --- relationships --------------------------------------------------------
    def relate(self, execution: ExecutionRecord, *, relation: str, target_id: str,
               target_kind: str, target_lineage_id: Optional[str] = None,
               created_at: str = DETERMINISTIC_EPOCH) -> ExecutionRelationship:
        """Create a versioned relationship Execution -> target (lineage-tracked)."""
        rel_id = mint_relationship(execution.execution_id, relation, target_id)
        parents = [execution.lineage_id] + ([target_lineage_id] if target_lineage_id else [])
        node = self.lineage.record(make_relationship_lineage(
            rel_id, parents=parents, relation=relation, created_at=created_at))
        self.audit.append("execution_relationship_added",
                          {"relationship_id": rel_id, "execution_id": execution.execution_id,
                           "relation": relation, "target_id": target_id,
                           "target_kind": target_kind, "lineage_id": node.lineage_id},
                          created_at=created_at)
        version = ExecutionVersion.compute(f"rel:{rel_id}", None)
        rel = ExecutionRelationship(relationship_id=rel_id,
                                    source_execution_id=execution.execution_id, relation=relation,
                                    target_id=target_id, target_kind=target_kind, version=version)
        self.registry.register_relationship(rel)
        return rel



    # --- lifecycle transition (governed) -------------------------------------
    def transition(self, execution: ExecutionRecord, target: ExecutionLifecycleState, *,
                   reason: str = "", approved: bool = False, authority: Optional[str] = None,
                   created_at: str = DETERMINISTIC_EPOCH) -> ExecutionRecord:
        """Move an execution to ``target`` (validated, governed, audited, versioned).

        Governed transitions (AUTHORIZED/ACTIVE/COMPLETED/TERMINATED) require a policy
        decision. If a ``policy_decider`` is injected it is consulted; otherwise the
        caller must pass ``approved=True``. ACTIVE additionally fails the gate unless
        authorized. PAUSED/BLOCKED/resume are operational (non-governed) transitions.
        """
        record = self.lifecycle.transition(execution.state, target, reason=reason,
                                            created_at=created_at)
        decision, policy_id = "n/a", None
        authorization_approved = True
        if self.lifecycle.requires_policy(target):
            hook = self.lifecycle.policy_hook(target)
            if self.policy_decider is not None:
                approved, decision, policy_id, authority = self.policy_decider(hook, execution)
            else:
                decision = "approved" if approved else "denied"
            authorization_approved = approved
            self.audit.append("execution_policy_decision",
                              {"execution_id": execution.execution_id, "hook": hook,
                               "decision": decision, "policy_id": policy_id, "approved": approved},
                              created_at=created_at)
            if not approved:
                execution.governance = execution.governance.with_event(
                    authorization_state="denied", authority=authority, hook=hook,
                    decision=decision, policy_id=policy_id, created_at=created_at)
                self._finalize(execution, reason=f"policy_denied:{hook}", created_at=created_at)
                raise ExecutionGovernanceError(
                    f"transition {execution.state.value}->{target.value} denied by policy ({hook})")
            # AUTHORIZED/ACTIVE mark the execution authorized; later governed transitions keep it
            auth_state = "authorized" if target in (
                ExecutionLifecycleState.AUTHORIZED, ExecutionLifecycleState.ACTIVE) \
                else execution.governance.authorization_state
            execution.governance = execution.governance.with_event(
                authorization_state=auth_state, authority=authority, hook=hook, decision=decision,
                policy_id=policy_id, created_at=created_at)

        report = self.gate.evaluate(execution=execution, parents=(execution.lineage_id,),
                                    requires_lineage=True, target_state=target,
                                    authorization_approved=authorization_approved)
        self.gate.raise_if_failed(report)

        self.audit.append("execution_state_change", record.to_dict(), created_at=created_at)
        node = self.lineage.record(make_execution_lineage(
            execution.execution_id, parents=(execution.lineage_id,),
            reason=f"{record.from_state}->{record.to_state}", created_at=created_at,
            extra={"transition": record.to_dict()}))
        execution.state = target
        execution.lineage_id = node.lineage_id
        execution.status = observe(execution)              # refresh the read-only status
        self._finalize(execution, reason=f"transition:{record.from_state}->{record.to_state}",
                       created_at=created_at)
        return execution

    # --- monitoring (observe only; never modifies execution truth) -----------
    def observe(self, execution: ExecutionRecord):
        return observe(execution)

    # --- validation + reports -------------------------------------------------
    def validate(self, execution: ExecutionRecord):
        return self.validator.validate(execution=execution, registry=self.registry,
                                       audit_log=self.audit, lineage_tracker=self.lineage)

    def reports(self, executions: Sequence) -> dict:
        executions = list(executions)
        return {
            "execution_summary_report": build_execution_summary_report(executions),
            "authorization_report": build_authorization_report(executions),
            "status_report": build_status_report(executions),
            "monitoring_report": build_monitoring_report(executions),
            "execution_governance_report": build_execution_governance_report(executions),
            "execution_audit_report": build_execution_audit_report(self.audit),
            "execution_lineage_report": build_execution_lineage_report(executions, self.lineage),
        }

    def validation_report(self, scope: str, validation_report_dict: dict) -> dict:
        return build_execution_validation_report(scope, validation_report_dict)

    # --- internals ------------------------------------------------------------
    def _finalize(self, execution: ExecutionRecord, *, reason: str, created_at: str) -> None:
        """Bump the execution version (chained), audit it, then sync the registry."""
        previous = execution.version or None
        new_version = ExecutionVersion.compute(execution.state_signature(), previous)
        execution.previous_version = previous
        execution.version = new_version
        self.audit.append("execution_version_changed",
                          {"execution_id": execution.execution_id, "version": new_version,
                           "reason": reason}, created_at=created_at)
        execution.audit_state = self.audit.head
        ctx = execution.context
        self.registry.register(ExecutionRegistryRecord(
            execution_id=execution.execution_id, source_task_id=ctx.task_id,
            assignment_id=execution.assignment_id, state=execution.state.value,
            version=new_version, authorization_state=execution.governance.authorization_state,
            agent_references=((ctx.agent_id,) if ctx.agent_id else ()),
            task_references=((ctx.task_id,) if ctx.task_id else ()),
            policy_references=execution.governance.policy_references,
            lineage_id=execution.lineage_id, audit_state=execution.audit_state,
            content_signature_value=execution.state_signature()))
        self.audit.append("execution_registered",
                          {"execution_id": execution.execution_id, "version": new_version},
                          created_at=created_at)
        execution.audit_state = self.audit.head
