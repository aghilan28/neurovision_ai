"""Workstation state: load + expose the registered-artifact snapshot.

The workstation's only contract with the rest of the system is the **snapshot**
written by ``scripts.build_workstation_snapshot`` — a JSON document containing
every registered artifact (registries, reports, immutable audit logs, the lineage
graph, validation results) for the composed Version 2 services. The workstation
reads it with stdlib ``json`` and imports **no** domain code (NR-8).

It never creates source-of-truth state. The only state it tracks is *navigation
context* (current patient / case / review / finding / …), and every transition is
deterministic: setting a context just records the chosen id; nothing is computed
or mutated. The workstation is a presentation layer, not a source of truth.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..version import WORKSTATION_STATE_VERSION


def _load(path: str) -> dict:
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


# The deterministic navigation-context keys the workstation tracks.
CONTEXT_KEYS = (
    "current_patient", "current_case", "current_review", "current_finding",
    "current_knowledge", "current_intelligence", "current_decision",
    "current_audit", "current_lineage",
)


@dataclass
class WorkstationState:
    """Loaded, read-only view of one workstation snapshot + navigation context."""

    snapshot: dict
    context: dict = field(default_factory=dict)
    state_version: str = WORKSTATION_STATE_VERSION

    # ---- loading -------------------------------------------------------------
    @classmethod
    def load(cls, snapshot_path: str) -> "WorkstationState":
        return cls(snapshot=_load(snapshot_path))

    @classmethod
    def from_snapshot(cls, snapshot: dict) -> "WorkstationState":
        return cls(snapshot=dict(snapshot))

    # ---- top-level accessors -------------------------------------------------
    @property
    def cases(self) -> list:
        return self.snapshot.get("cases", [])

    @property
    def reviews(self) -> list:
        return self.snapshot.get("reviews", [])

    @property
    def findings(self) -> list:
        return self.snapshot.get("findings", [])

    @property
    def knowledge(self) -> dict:
        return self.snapshot.get("knowledge", {})

    @property
    def intelligence(self) -> dict:
        return self.snapshot.get("intelligence", {})

    @property
    def decision_support(self) -> dict:
        return self.snapshot.get("decision_support", {})

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

    # ---- record lookups (by id) ---------------------------------------------
    def case(self, case_id: str) -> dict:
        return self._find(self.cases, "case_id", case_id)

    def review(self, review_id: str) -> dict:
        return self._find(self.reviews, "review_id", review_id)

    def finding(self, finding_id: str) -> dict:
        return self._find(self.findings, "finding_id", finding_id)

    def decision_bundle(self, case_id: str) -> dict:
        return self._find(self.decision_support.get("bundles", []), "case_id", case_id)

    def reviews_for_case(self, case_id: str) -> list:
        return [r for r in self.reviews if r.get("case_id") == case_id]

    def findings_for_case(self, case_id: str) -> list:
        return [f for f in self.findings if f.get("case_id") == case_id]

    @staticmethod
    def _find(items: list, key: str, value: str) -> dict:
        for it in items:
            if it.get(key) == value:
                return it
        return {}

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
        if self.cases:
            c = self.cases[0]
            self.context["current_case"] = c.get("case_id")
            self.context["current_patient"] = c.get("patient_id")
        if self.reviews:
            self.context["current_review"] = self.reviews[0].get("review_id")
        if self.findings:
            self.context["current_finding"] = self.findings[0].get("finding_id")
        self.context["current_knowledge"] = "knowledge"
        self.context["current_intelligence"] = (
            self.intelligence.get("analytics", {}).get("artifact", {}).get("analytics_id"))
        if self.decision_support.get("bundles"):
            self.context["current_decision"] = self.decision_support["bundles"][0].get("record_id")
        rep = self.representative_chain.get("records", [])
        self.context["current_lineage"] = rep[0]["lineage_id"] if rep else None
        self.context["current_audit"] = self.context.get("current_case")
        return self

    def context_snapshot(self) -> dict:
        """The full deterministic context (all keys present, unset -> None)."""
        return {k: self.context.get(k) for k in CONTEXT_KEYS}
