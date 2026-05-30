"""TaskService — the governed orchestration hub for the Task Intelligence Layer.

Ties identity, taxonomy, lifecycle, governance, dependencies, registry, audit, and
lineage into the use cases that derive a Task from a ready Plan, relate tasks, and
move a task through its lifecycle. Every mutation is: governance-gated -> audited
(immutable) -> lineage-extended -> version-bumped -> registry-synced.

A **Task** describes work — it never executes. The transition into READY (and the
other governed transitions) requires a **policy decision**: the service calls an
injected ``policy_decider`` (the V4-P2 policy engine, wired by the integration
layer). If none is injected, governed transitions require an explicit caller
``approved=True``. **Every task must derive from a ready plan**: ``create_task``
requires a source plan whose lineage node is supplied and whose state is asserted by
the caller (the plan service owns plan readiness). Shares the platform's single
``ml.lineage.LineageTracker`` and the shared ``ImmutableAuditLog`` — no parallel
lineage/audit/governance.
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence

from ml.lineage import LineageTracker  # allowed: backend -> ml

from .version import DETERMINISTIC_EPOCH
from .identity import mint_task, mint_relationship
from .taxonomy import validate_category, validate_relation, is_priority, TaskPriority
from .lifecycle import TaskLifecycle, TaskLifecycleState
from .governance import TaskGovernanceGate, TaskGovernanceError
from .registry import TaskRegistry
from .validation import TaskValidator
from .audit import make_task_audit_log
from .lineage import make_task_lineage, make_relationship_lineage
from .models.domain import (
    TaskMetadata, TaskGovernanceRecord, TaskConstraintReference, TaskDependency,
    TaskVersion, TaskRegistryRecord, TaskRecord,
)
from .reports import (
    build_task_summary_report, build_task_registry_report, build_task_lifecycle_report,
    build_task_dependency_report, build_task_governance_report, build_task_validation_report,
    build_task_audit_report, build_task_lineage_report,
)

# A policy decider takes (hook, task) and returns (approved, decision, policy_id, authority).
PolicyDecider = Callable[[str, TaskRecord], tuple]


class TaskDerivationError(RuntimeError):
    """Raised when a task is derived from a plan that is not ready/completed."""


# plan states from which a task may be derived (a plan must be READY to break down
# into work; "completed" is accepted for archival/audit derivation).
_DERIVABLE_PLAN_STATES = frozenset({"ready", "completed"})



class TaskService:
    """Stateful service: task registry, shared lineage tracker, immutable audit log."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[TaskRegistry] = None,
                 policy_decider: Optional[PolicyDecider] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or TaskRegistry()
        self.audit = make_task_audit_log()
        self.lifecycle = TaskLifecycle()
        self.gate = TaskGovernanceGate()
        self.validator = TaskValidator()
        self.policy_decider = policy_decider

    # --- create (derive from a ready plan) -----------------------------------
    def create_task(self, *, category: str, task_key: str, metadata: TaskMetadata,
                    source_plan_id: str, source_plan_lineage_id: str, source_plan_state: str,
                    source_goal_id: str = "", priority: str = TaskPriority.MEDIUM,
                    dependencies: Sequence[str] = (), extra_parents: Sequence[str] = (),
                    owner: str = "task-ops",
                    created_at: str = DETERMINISTIC_EPOCH) -> TaskRecord:
        """Derive a PROPOSED task from a ready plan (governance-gated, lineage-rooted).

        Every task must derive from a ready plan — the caller supplies the source
        plan id, its lineage node, and its lifecycle state (owned by the plan service).
        """
        validate_category(category)
        if not is_priority(priority):
            raise ValueError(f"invalid task priority {priority!r}")
        if source_plan_state not in _DERIVABLE_PLAN_STATES:
            raise TaskDerivationError(
                f"cannot derive a task from plan {source_plan_id} in state "
                f"{source_plan_state!r} (must be ready/completed)")
        ident = mint_task(category, source_plan_id, task_key)
        task = TaskRecord(
            task_id=ident.id, category=category, source_plan_id=source_plan_id, task_key=task_key,
            metadata=metadata, priority=priority, state=TaskLifecycleState.PROPOSED,
            governance=TaskGovernanceRecord(), source_goal_id=source_goal_id,
            dependencies=tuple(dependencies), owner=owner, created_at=created_at)

        # parents: the source plan's lineage node (so the task traces to the patient)
        # plus any explicit extra parents and dependency tasks' lineage nodes.
        parents = [source_plan_lineage_id] + list(extra_parents)
        for dep in dependencies:
            if self.registry.exists(dep):
                parents.append(self.registry.get(dep).lineage_id)
        report = self.gate.evaluate(task=task, parents=tuple(parents), requires_lineage=True)
        self.gate.raise_if_failed(report)

        node = self.lineage.record(make_task_lineage(
            task.task_id, parents=parents, category=category, reason="created",
            created_at=created_at))
        self.audit.append("task_created",
                          {"task_id": task.task_id, "category": category,
                           "source_plan_id": source_plan_id, "lineage_id": node.lineage_id,
                           "n_parents": len(parents)}, created_at=created_at)
        task.lineage_id = node.lineage_id
        self.audit.append("task_plan_linked",
                          {"task_id": task.task_id, "plan_id": source_plan_id},
                          created_at=created_at)
        self._finalize(task, reason="created", created_at=created_at)
        return task

    # --- attach a constraint reference (Task<->Policy) -----------------------
    def attach_constraint(self, task: TaskRecord, constraint: TaskConstraintReference,
                          created_at: str = DETERMINISTIC_EPOCH) -> TaskRecord:
        task.constraints = task.constraints + (constraint,)
        task.governance = task.governance.with_constraint(constraint.constraint_id)
        self.audit.append("task_constraint_attached",
                          {"task_id": task.task_id, "constraint_id": constraint.constraint_id,
                           "hook": constraint.hook}, created_at=created_at)
        self._finalize(task, reason=f"attach_constraint:{constraint.constraint_id}",
                       created_at=created_at)
        return task

    # --- dependencies / relationships ----------------------------------------
    def relate(self, task: TaskRecord, *, relation: str, target_id: str, target_kind: str,
               target_lineage_id: Optional[str] = None,
               created_at: str = DETERMINISTIC_EPOCH) -> TaskDependency:
        """Create a versioned dependency Task -> target (lineage-tracked)."""
        validate_relation(relation, target_kind)
        dep_id = mint_relationship(task.task_id, relation, target_id)
        parents = [task.lineage_id] + ([target_lineage_id] if target_lineage_id else [])
        node = self.lineage.record(make_relationship_lineage(
            dep_id, parents=parents, relation=relation, created_at=created_at))
        self.audit.append("task_dependency_added",
                          {"dependency_id": dep_id, "task_id": task.task_id,
                           "relation": relation, "target_id": target_id,
                           "target_kind": target_kind, "lineage_id": node.lineage_id},
                          created_at=created_at)
        version = TaskVersion.compute(f"dep:{dep_id}", None)
        dep = TaskDependency(dependency_id=dep_id, source_task_id=task.task_id,
                             relation=relation, target_id=target_id, target_kind=target_kind,
                             version=version)
        self.registry.register_dependency(dep)
        if relation in ("depends_on", "requires") and target_kind == "task" \
                and target_id not in task.dependencies:
            task.dependencies = task.dependencies + (target_id,)
            self._finalize(task, reason=f"relate:{relation}:{target_id}", created_at=created_at)
        return dep



    # --- lifecycle transition (governed) -------------------------------------
    def transition(self, task: TaskRecord, target: TaskLifecycleState, *, reason: str = "",
                   approved: bool = False, authority: Optional[str] = None,
                   created_at: str = DETERMINISTIC_EPOCH) -> TaskRecord:
        """Move a task to ``target`` (validated, governed, audited, versioned).

        Governed transitions (APPROVED/READY/COMPLETED) require a policy decision. If
        a ``policy_decider`` is injected it is consulted; otherwise the caller must
        pass ``approved=True``. READY additionally fails the gate unless approved.
        BLOCKED/un-block are operational (non-governed) transitions.
        """
        record = self.lifecycle.transition(task.state, target, reason=reason,
                                            created_at=created_at)

        decision, policy_id = "n/a", None
        readiness_approved = True
        if self.lifecycle.requires_policy(target):
            hook = self.lifecycle.policy_hook(target)
            if self.policy_decider is not None:
                approved, decision, policy_id, authority = self.policy_decider(hook, task)
            else:
                decision = "approved" if approved else "denied"
            readiness_approved = approved
            self.audit.append("task_policy_decision",
                              {"task_id": task.task_id, "hook": hook, "decision": decision,
                               "policy_id": policy_id, "approved": approved},
                              created_at=created_at)
            if not approved:
                task.governance = task.governance.with_event(
                    approval_state="rejected", authority=authority, hook=hook,
                    decision=decision, policy_id=policy_id, created_at=created_at)
                self._finalize(task, reason=f"policy_denied:{hook}", created_at=created_at)
                raise TaskGovernanceError(
                    f"transition {task.state.value}->{target.value} denied by policy ({hook})")
            task.governance = task.governance.with_event(
                approval_state="approved", authority=authority, hook=hook, decision=decision,
                policy_id=policy_id, created_at=created_at)

        report = self.gate.evaluate(task=task, parents=(task.lineage_id,), requires_lineage=True,
                                    target_state=target, readiness_approved=readiness_approved)
        self.gate.raise_if_failed(report)

        self.audit.append("task_state_change", record.to_dict(), created_at=created_at)
        node = self.lineage.record(make_task_lineage(
            task.task_id, parents=(task.lineage_id,), category=task.category,
            reason=f"{record.from_state}->{record.to_state}", created_at=created_at,
            extra={"transition": record.to_dict()}))
        task.state = target
        task.lineage_id = node.lineage_id
        self._finalize(task, reason=f"transition:{record.from_state}->{record.to_state}",
                       created_at=created_at)
        return task

    # --- validation + reports -------------------------------------------------
    def validate(self, task: TaskRecord):
        return self.validator.validate(task=task, registry=self.registry,
                                       audit_log=self.audit, lineage_tracker=self.lineage)

    def reports(self, tasks: Sequence) -> dict:
        tasks = list(tasks)
        return {
            "task_summary_report": build_task_summary_report(tasks),
            "task_registry_report": build_task_registry_report(self.registry),
            "task_lifecycle_report": build_task_lifecycle_report(tasks),
            "task_dependency_report": build_task_dependency_report(self.registry),
            "task_governance_report": build_task_governance_report(tasks),
            "task_audit_report": build_task_audit_report(self.audit),
            "task_lineage_report": build_task_lineage_report(tasks, self.lineage),
        }

    def validation_report(self, scope: str, validation_report_dict: dict) -> dict:
        return build_task_validation_report(scope, validation_report_dict)

    # --- internals ------------------------------------------------------------
    def _finalize(self, task: TaskRecord, *, reason: str, created_at: str) -> None:
        """Bump the task version (chained), audit it, then sync the registry."""
        previous = task.version or None
        new_version = TaskVersion.compute(task.state_signature(), previous)
        task.previous_version = previous
        task.version = new_version
        self.audit.append("task_version_changed",
                          {"task_id": task.task_id, "version": new_version, "reason": reason},
                          created_at=created_at)
        task.audit_state = self.audit.head
        self.registry.register(TaskRegistryRecord(
            task_id=task.task_id, category=task.category, source_plan_id=task.source_plan_id,
            state=task.state.value, priority=task.priority, version=new_version,
            approval_state=task.governance.approval_state, dependencies=task.dependencies,
            plan_references=(task.source_plan_id,),
            goal_references=((task.source_goal_id,) if task.source_goal_id else ()),
            policy_references=task.governance.policy_references, lineage_id=task.lineage_id,
            audit_state=task.audit_state, content_signature_value=task.state_signature()))
        self.audit.append("task_registered",
                          {"task_id": task.task_id, "version": new_version}, created_at=created_at)
        task.audit_state = self.audit.head
