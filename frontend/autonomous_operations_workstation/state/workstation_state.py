"""Autonomous-operations workstation state: load + expose the snapshot (V4-P8).

The workstation's only contract with the rest of the system is the **snapshot**
written by ``scripts.build_autonomous_operations_workstation_snapshot`` — a JSON
document containing every registered artifact (registries, reports, immutable audit
logs, the lineage graph, validation results) for the composed Version 4 services plus
the V4-P7 Governance Intelligence Layer. The workstation reads it with stdlib
``json`` and imports **no** domain code (NR-8).

It never creates source-of-truth state. The only state it tracks is *navigation
context* (current goal / policy / plan / task / agent / execution / governance /
audit / lineage), and every transition is deterministic: setting a context just
records the chosen id; nothing is computed or mutated. The workstation is a
presentation + human-oversight layer, not a source of truth.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..version import AOW_STATE_VERSION


def _load(path: str) -> dict:
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


# the deterministic navigation-context keys the workstation tracks.
CONTEXT_KEYS = (
    "current_goal", "current_policy", "current_plan", "current_task", "current_agent",
    "current_execution", "current_governance", "current_audit", "current_lineage",
)

# the governed entity blocks (in deliverable-chain order).
ENTITY_BLOCKS = ("goals", "policies", "plans", "tasks", "agents", "executions")


@dataclass
class WorkstationState:
    """Loaded, read-only view of one workstation snapshot + navigation context."""

    snapshot: dict
    context: dict = field(default_factory=dict)
    state_version: str = AOW_STATE_VERSION

    # ---- loading -------------------------------------------------------------
    @classmethod
    def load(cls, snapshot_path: str) -> "WorkstationState":
        return cls(snapshot=_load(snapshot_path))

    @classmethod
    def from_snapshot(cls, snapshot: dict) -> "WorkstationState":
        return cls(snapshot=dict(snapshot))

    # ---- top-level accessors -------------------------------------------------
    def block(self, name: str) -> dict:
        return self.snapshot.get(name, {})

    @property
    def goals(self) -> dict:
        return self.block("goals")

    @property
    def policies(self) -> dict:
        return self.block("policies")

    @property
    def plans(self) -> dict:
        return self.block("plans")

    @property
    def tasks(self) -> dict:
        return self.block("tasks")

    @property
    def agents(self) -> dict:
        return self.block("agents")

    @property
    def executions(self) -> dict:
        return self.block("executions")

    @property
    def governance(self) -> dict:
        return self.block("governance")

    @property
    def lineage(self) -> dict:
        return self.block("lineage")

    @property
    def representative_chain(self) -> dict:
        return self.snapshot.get("representative_chain", {})

    @property
    def meta(self) -> dict:
        return self.snapshot.get("meta", {})

    # ---- record collections --------------------------------------------------
    def records(self, block: str) -> list:
        return self.block(block).get("records", [])

    def record(self, block: str, record_id: str) -> dict:
        for r in self.records(block):
            if r.get("id") == record_id:
                return r
        return {}

    def constraints(self) -> list:
        return self.policies.get("constraints", [])

    # governance intelligence sub-collections
    def approvals(self) -> list:
        return self.governance.get("approvals", [])

    def violations(self) -> list:
        return self.governance.get("violations", [])

    def escalations(self) -> list:
        return self.governance.get("escalations", [])

    def risks(self) -> list:
        return self.governance.get("risks", [])

    def metrics(self) -> list:
        return self.governance.get("metrics", [])

    def monitoring(self) -> dict:
        return self.governance.get("monitoring", {})

    # ---- audit logs (every subsystem) ---------------------------------------
    def audit_logs(self) -> list:
        """(scope, audit_dict) for every immutable audit log in the snapshot."""
        out = []
        for scope in (*ENTITY_BLOCKS, "governance"):
            block = self.snapshot.get(scope, {})
            if block.get("audit"):
                out.append((scope, block["audit"]))
        return out

    # ---- reports (every subsystem) ------------------------------------------
    def reports_blocks(self) -> list:
        """(scope, reports_dict) for every subsystem that exposes registered reports."""
        out = []
        for scope in (*ENTITY_BLOCKS, "governance"):
            block = self.snapshot.get(scope, {})
            if block.get("reports"):
                out.append((scope, block["reports"]))
        return out

    # ---- navigation context (deterministic; presentation-only) --------------
    def set_context(self, **kwargs) -> "WorkstationState":
        for key, value in kwargs.items():
            if key not in CONTEXT_KEYS:
                raise KeyError(f"unknown context key {key!r}; valid: {CONTEXT_KEYS}")
            self.context[key] = value
        return self

    def default_context(self) -> "WorkstationState":
        """Seed a deterministic default context from the first available artifacts."""
        def first_id(block: str):
            recs = self.records(block)
            return recs[0].get("id") if recs else None

        self.context["current_goal"] = first_id("goals")
        self.context["current_policy"] = first_id("policies")
        self.context["current_plan"] = first_id("plans")
        self.context["current_task"] = first_id("tasks")
        self.context["current_agent"] = first_id("agents")
        self.context["current_execution"] = first_id("executions")
        intel = self.governance.get("intelligence", {})
        self.context["current_governance"] = intel.get("intelligence_id")
        self.context["current_audit"] = "goals"
        rep = self.representative_chain.get("records", [])
        self.context["current_lineage"] = rep[0]["lineage_id"] if rep else None
        return self

    def context_snapshot(self) -> dict:
        return {k: self.context.get(k) for k in CONTEXT_KEYS}
