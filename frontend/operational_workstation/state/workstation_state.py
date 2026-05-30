"""Operational workstation state: load + expose the registered-artifact snapshot.

The workstation's only contract with the rest of the system is the **snapshot**
written by ``scripts.build_operational_workstation_snapshot`` — a JSON document
containing every registered artifact (registries, reports, immutable audit logs,
the lineage graph, validation results) for the composed Version 3 services. The
workstation reads it with stdlib ``json`` and imports **no** domain code (NR-8).

It never creates source-of-truth state. The only state it tracks is *navigation
context* (current event / timeline / workflow / graph / analytics / recommendation
/ audit / lineage), and every transition is deterministic: setting a context just
records the chosen id; nothing is computed or mutated. The workstation is a
presentation layer, not a source of truth.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..version import OPERATIONAL_STATE_VERSION


def _load(path: str) -> dict:
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


# The deterministic navigation-context keys the workstation tracks.
CONTEXT_KEYS = (
    "current_event", "current_timeline", "current_workflow", "current_graph",
    "current_analytics", "current_recommendation", "current_audit", "current_lineage",
)


@dataclass
class WorkstationState:
    """Loaded, read-only view of one operational snapshot + navigation context."""

    snapshot: dict
    context: dict = field(default_factory=dict)
    state_version: str = OPERATIONAL_STATE_VERSION

    # ---- loading -------------------------------------------------------------
    @classmethod
    def load(cls, snapshot_path: str) -> "WorkstationState":
        return cls(snapshot=_load(snapshot_path))

    @classmethod
    def from_snapshot(cls, snapshot: dict) -> "WorkstationState":
        return cls(snapshot=dict(snapshot))

    # ---- top-level accessors (each a registered-artifact block) --------------
    @property
    def events(self) -> dict:
        return self.snapshot.get("events", {})

    @property
    def timelines(self) -> dict:
        return self.snapshot.get("timelines", {})

    @property
    def workflows(self) -> dict:
        return self.snapshot.get("workflows", {})

    @property
    def graph(self) -> dict:
        return self.snapshot.get("graph", {})

    @property
    def analytics(self) -> dict:
        return self.snapshot.get("analytics", {})

    @property
    def recommendations(self) -> dict:
        return self.snapshot.get("recommendations", {})

    @property
    def lineage(self) -> dict:
        return self.snapshot.get("lineage", {})

    @property
    def registries(self) -> dict:
        return self.snapshot.get("registries", {})

    @property
    def representative_chain(self) -> dict:
        return self.snapshot.get("representative_chain", {})

    @property
    def meta(self) -> dict:
        return self.snapshot.get("meta", {})

    # ---- record collections --------------------------------------------------
    @property
    def event_records(self) -> list:
        return self.events.get("events", [])

    @property
    def workflow_records(self) -> list:
        return self.workflows.get("workflows", [])

    @property
    def analytics_blocks(self) -> dict:
        return self.analytics.get("blocks", {})

    @property
    def recommendation_records(self) -> list:
        return self.recommendations.get("recommendations", [])



    # ---- record lookups (by id) ---------------------------------------------
    def event(self, event_id: str) -> dict:
        return self._find(self.event_records, "event_id", event_id)

    def workflow(self, workflow_id: str) -> dict:
        return self._find(self.workflow_records, "workflow_id", workflow_id)

    def recommendation(self, recommendation_id: str) -> dict:
        return self._find(self.recommendation_records, "recommendation_id", recommendation_id)

    def analytics_block(self, category: str) -> dict:
        return self.analytics_blocks.get(category, {})

    @staticmethod
    def _find(items: list, key: str, value: str) -> dict:
        for it in items:
            if it.get(key) == value:
                return it
        return {}

    # ---- audit logs (every subsystem) ---------------------------------------
    def audit_logs(self) -> list:
        """(scope, audit_dict) for every immutable audit log in the snapshot."""
        out = []
        for scope in ("events", "timelines", "workflows", "graph", "analytics",
                      "recommendations"):
            block = self.snapshot.get(scope, {})
            if block.get("audit"):
                out.append((scope, block["audit"]))
        return out

    # ---- navigation context (deterministic; presentation-only) --------------
    def set_context(self, **kwargs) -> "WorkstationState":
        """Set one or more navigation-context keys (deterministic, no computation)."""
        for key, value in kwargs.items():
            if key not in CONTEXT_KEYS:
                raise KeyError(f"unknown context key {key!r}; valid: {CONTEXT_KEYS}")
            self.context[key] = value
        return self

    def default_context(self) -> "WorkstationState":
        """Seed a deterministic default context from the first available artifacts."""
        evs = self.event_records
        self.context["current_event"] = evs[0].get("event_id") if evs else None
        op_tl = self.timelines.get("operational_timeline", {}).get("artifact", {})
        self.context["current_timeline"] = op_tl.get("timeline_id") or op_tl.get("artifact_id")
        wfs = self.workflow_records
        self.context["current_workflow"] = wfs[0].get("workflow_id") if wfs else None
        proj = self.graph.get("projection", {}).get("artifact", {})
        self.context["current_graph"] = proj.get("projection_id")
        op_block = self.analytics_blocks.get("operational", {}).get("artifact", {})
        self.context["current_analytics"] = op_block.get("analytics_id")
        recs = self.recommendation_records
        self.context["current_recommendation"] = recs[0].get("recommendation_id") if recs else None
        self.context["current_audit"] = "events"
        rep = self.representative_chain.get("records", [])
        self.context["current_lineage"] = rep[0]["lineage_id"] if rep else None
        return self

    def context_snapshot(self) -> dict:
        """The full deterministic context (all keys present, unset -> None)."""
        return {k: self.context.get(k) for k in CONTEXT_KEYS}
