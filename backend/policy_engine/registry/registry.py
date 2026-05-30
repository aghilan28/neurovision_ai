"""The policy registry: governed policies, constraints, and evaluations (V4-P2).

No policy may exist outside the registry. Re-registering the same id + version with
different content is a forbidden silent overwrite. The registry tracks policies
(category, state, approval, version, constraint refs, audit + lineage refs), the
versioned constraints, and the immutable evaluation records.
"""

from __future__ import annotations

from ..version import POLICY_REGISTRY_VERSION
from ..models.domain import PolicyRegistryRecord, ConstraintRecord, PolicyEvaluation


class PolicyRegistry:
    """In-memory registry: policies (versioned) + constraints + evaluations."""

    def __init__(self) -> None:
        self._policies: dict[str, PolicyRegistryRecord] = {}
        self._version_sigs: dict[tuple[str, str], str] = {}
        self._constraints: dict[str, ConstraintRecord] = {}
        self._evaluations: dict[str, PolicyEvaluation] = {}

    # --- policies -------------------------------------------------------------
    def register(self, record: PolicyRegistryRecord) -> PolicyRegistryRecord:
        key = (record.policy_id, record.version)
        sig = record.content_signature()
        if key in self._version_sigs and self._version_sigs[key] != sig:
            raise ValueError(
                f"policy {record.policy_id} version {record.version} already registered "
                "with different content (silent overwrite forbidden)")
        self._version_sigs[key] = sig
        self._policies[record.policy_id] = record
        return record

    def get(self, policy_id: str) -> PolicyRegistryRecord:
        if policy_id not in self._policies:
            raise KeyError(f"policy {policy_id!r} not in registry")
        return self._policies[policy_id]

    def exists(self, policy_id: str) -> bool:
        return policy_id in self._policies

    def list_policies(self) -> list[str]:
        return sorted(self._policies)

    def by_category(self, category: str) -> list[str]:
        return sorted(pid for pid, r in self._policies.items() if r.category == category)

    def active_policies(self) -> list[str]:
        return sorted(pid for pid, r in self._policies.items() if r.state == "active")

    # --- constraints ----------------------------------------------------------
    def register_constraint(self, c: ConstraintRecord) -> ConstraintRecord:
        existing = self._constraints.get(c.constraint_id)
        if existing is not None and existing.state_signature() != c.state_signature():
            raise ValueError(f"constraint {c.constraint_id} already registered with "
                             "different content (silent overwrite forbidden)")
        self._constraints[c.constraint_id] = c
        return c

    def constraint(self, constraint_id: str) -> ConstraintRecord:
        if constraint_id not in self._constraints:
            raise KeyError(f"constraint {constraint_id!r} not in registry")
        return self._constraints[constraint_id]

    def has_constraint(self, constraint_id: str) -> bool:
        return constraint_id in self._constraints

    def list_constraints(self) -> list[str]:
        return sorted(self._constraints)

    def constraints_for(self, policy_record) -> list[ConstraintRecord]:
        return [self._constraints[cid] for cid in policy_record.constraint_ids
                if cid in self._constraints]

    # --- evaluations ----------------------------------------------------------
    def register_evaluation(self, e: PolicyEvaluation) -> PolicyEvaluation:
        existing = self._evaluations.get(e.evaluation_id)
        if existing is not None and existing.state_signature() != e.state_signature():
            raise ValueError(f"evaluation {e.evaluation_id} already registered with "
                             "different content (silent overwrite forbidden)")
        self._evaluations[e.evaluation_id] = e
        return e

    def evaluation(self, evaluation_id: str) -> PolicyEvaluation:
        if evaluation_id not in self._evaluations:
            raise KeyError(f"evaluation {evaluation_id!r} not in registry")
        return self._evaluations[evaluation_id]

    def list_evaluations(self) -> list[str]:
        return sorted(self._evaluations)

    def to_dict(self) -> dict:
        return {"policy_registry_version": POLICY_REGISTRY_VERSION,
                "n_policies": len(self._policies), "n_constraints": len(self._constraints),
                "n_evaluations": len(self._evaluations),
                "policies": {pid: r.to_dict() for pid, r in sorted(self._policies.items())},
                "constraints": {cid: c.to_dict()
                                for cid, c in sorted(self._constraints.items())},
                "evaluations": {eid: e.to_dict()
                                for eid, e in sorted(self._evaluations.items())}}
