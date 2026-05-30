"""The plan registry: governed, versioned, traceable plans + dependencies (V4-P3).

No plan may exist outside the registry. Re-registering the same id + version with
different content is a forbidden silent overwrite. The registry tracks plans (type,
status, priority, goal/policy references, dependencies, audit + lineage refs) and
the versioned plan dependencies.
"""

from __future__ import annotations

from ..version import PLAN_REGISTRY_VERSION
from ..models.domain import PlanRegistryRecord, PlanDependency


class PlanRegistry:
    """In-memory registry keyed by ``plan_id`` (+ a dependency store)."""

    def __init__(self) -> None:
        self._records: dict[str, PlanRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}
        self._dependencies: dict[str, PlanDependency] = {}

    # --- plans ----------------------------------------------------------------
    def register(self, record: PlanRegistryRecord) -> PlanRegistryRecord:
        key = (record.plan_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"plan {record.plan_id} version {record.version} already registered "
                "with different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._records[record.plan_id] = record
        return record

    def get(self, plan_id: str) -> PlanRegistryRecord:
        if plan_id not in self._records:
            raise KeyError(f"plan {plan_id!r} not in registry")
        return self._records[plan_id]

    def exists(self, plan_id: str) -> bool:
        return plan_id in self._records

    def list_plans(self) -> list[str]:
        return sorted(self._records)

    def by_category(self, category: str) -> list[str]:
        return sorted(pid for pid, r in self._records.items() if r.category == category)

    def by_state(self, state: str) -> list[str]:
        return sorted(pid for pid, r in self._records.items() if r.state == state)

    def for_goal(self, goal_id: str) -> list[str]:
        return sorted(pid for pid, r in self._records.items() if r.source_goal_id == goal_id)

    # --- dependencies ---------------------------------------------------------
    def register_dependency(self, dep: PlanDependency) -> PlanDependency:
        existing = self._dependencies.get(dep.dependency_id)
        if existing is not None and existing.state_signature() != dep.state_signature():
            raise ValueError(f"dependency {dep.dependency_id} already registered with "
                             "different content (silent overwrite forbidden)")
        self._dependencies[dep.dependency_id] = dep
        return dep

    def dependency(self, dependency_id: str) -> PlanDependency:
        if dependency_id not in self._dependencies:
            raise KeyError(f"dependency {dependency_id!r} not in registry")
        return self._dependencies[dependency_id]

    def list_dependencies(self) -> list[str]:
        return sorted(self._dependencies)

    def dependencies_for(self, plan_id: str) -> list[PlanDependency]:
        return [d for d in self._dependencies.values() if d.source_plan_id == plan_id]

    def to_dict(self) -> dict:
        return {"plan_registry_version": PLAN_REGISTRY_VERSION,
                "n_plans": len(self._records), "n_dependencies": len(self._dependencies),
                "plans": {pid: r.to_dict() for pid, r in sorted(self._records.items())},
                "dependencies": {did: d.to_dict()
                                 for did, d in sorted(self._dependencies.items())}}
