"""The task registry: governed, versioned, traceable tasks + dependencies (V4-P4).

No task may exist outside the registry. Re-registering the same id + version with
different content is a forbidden silent overwrite. The registry tracks tasks (type,
status, priority, plan/goal references, dependencies, audit + lineage refs) and the
versioned task dependencies.
"""

from __future__ import annotations

from ..version import TASK_REGISTRY_VERSION
from ..models.domain import TaskRegistryRecord, TaskDependency


class TaskRegistry:
    """In-memory registry keyed by ``task_id`` (+ a dependency store)."""

    def __init__(self) -> None:
        self._records: dict[str, TaskRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}
        self._dependencies: dict[str, TaskDependency] = {}

    # --- tasks ----------------------------------------------------------------
    def register(self, record: TaskRegistryRecord) -> TaskRegistryRecord:
        key = (record.task_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"task {record.task_id} version {record.version} already registered "
                "with different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.task_id] = record
        return record

    def get(self, task_id: str) -> TaskRegistryRecord:
        if task_id not in self._records:
            raise KeyError(f"task {task_id!r} not in registry")
        return self._records[task_id]

    def exists(self, task_id: str) -> bool:
        return task_id in self._records

    def list_tasks(self) -> list[str]:
        return sorted(self._records)

    def by_category(self, category: str) -> list[str]:
        return sorted(tid for tid, r in self._records.items() if r.category == category)

    def by_state(self, state: str) -> list[str]:
        return sorted(tid for tid, r in self._records.items() if r.state == state)

    def for_plan(self, plan_id: str) -> list[str]:
        return sorted(tid for tid, r in self._records.items() if r.source_plan_id == plan_id)

    # --- dependencies ---------------------------------------------------------
    def register_dependency(self, dep: TaskDependency) -> TaskDependency:
        existing = self._dependencies.get(dep.dependency_id)
        if existing is not None and existing.state_signature() != dep.state_signature():
            raise ValueError(f"dependency {dep.dependency_id} already registered with "
                             "different content (silent overwrite forbidden)")
        self._dependencies[dep.dependency_id] = dep
        return dep

    def dependency(self, dependency_id: str) -> TaskDependency:
        if dependency_id not in self._dependencies:
            raise KeyError(f"dependency {dependency_id!r} not in registry")
        return self._dependencies[dependency_id]

    def list_dependencies(self) -> list[str]:
        return sorted(self._dependencies)

    def dependencies_for(self, task_id: str) -> list[TaskDependency]:
        return [d for d in self._dependencies.values() if d.source_task_id == task_id]

    def to_dict(self) -> dict:
        return {"task_registry_version": TASK_REGISTRY_VERSION,
                "n_tasks": len(self._records), "n_dependencies": len(self._dependencies),
                "tasks": {tid: r.to_dict() for tid, r in sorted(self._records.items())},
                "dependencies": {did: d.to_dict()
                                 for did, d in sorted(self._dependencies.items())}}
