"""Typed view-model contracts for the Autonomous Operations Workstation (V4-P8).

Pure presentation data structures (stdlib only — NR-8). They mirror the operational
workstation's view-models so the autonomous-operations workstation presents a single,
coherent human-oversight environment over every Version 4 subsystem (goals, policies,
plans, tasks, agents, executions) plus the V4-P7 Governance Intelligence Layer.

* ``Section``            — a renderable block (kv / table / badges / text).
* ``Visualization``      — a chart spec (bar / line / graph / timeline / table).
* ``InterventionControl``— a *governed* human-oversight control (suspend / pause /
                           terminate / escalate / request-review). It declares the
                           authorization it requires and the records it generates;
                           it never performs the action (the backend does).
* ``Page``               — one workspace view (sections + visualizations + controls).
* ``NavArea``            — a primary navigation area (id, title, pages, context).
* ``WorkstationView``    — the whole application view-model (nav + pages + validation).
* ``ValidationReport``   — the frontend's OWN tiny report (never imports ml.validation).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..version import AOW_VIEWMODEL_VERSION, AOW_CONTROL_VERSION


@dataclass(frozen=True)
class Section:
    kind: str          # "kv" | "table" | "badges" | "text"
    title: str
    data: dict
    viewmodel_version: str = AOW_VIEWMODEL_VERSION

    def to_dict(self) -> dict:
        return {"kind": self.kind, "title": self.title, "data": self.data,
                "viewmodel_version": self.viewmodel_version}


@dataclass(frozen=True)
class Visualization:
    type: str          # "bar" | "line" | "graph" | "timeline" | "table"
    title: str
    spec: dict

    def to_dict(self) -> dict:
        return {"type": self.type, "title": self.title, "spec": self.spec}


@dataclass(frozen=True)
class InterventionControl:
    """A governed human-oversight control surfaced (never performed) by the workstation.

    The workstation is observation/authorization/intervention/escalation surface —
    not execution/governance logic. A control therefore *describes* a governed
    backend action: the action, its target, the authorization it requires, and the
    records the backend will generate (audit + lineage + governance). ``enabled``
    reflects whether the target's observed state currently permits the action. No
    hidden actions: every control is explicit and fully attributed.
    """

    action: str                 # suspend_agent | pause_execution | terminate_execution | ...
    target_kind: str            # agent | execution
    target_id: str
    requires_authorization: bool = True
    generates_audit: bool = True
    generates_lineage: bool = True
    generates_governance_record: bool = True
    enabled: bool = True
    rationale: str = ""
    control_version: str = AOW_CONTROL_VERSION

    def to_dict(self) -> dict:
        return {"action": self.action, "target_kind": self.target_kind,
                "target_id": self.target_id,
                "requires_authorization": self.requires_authorization,
                "generates_audit": self.generates_audit,
                "generates_lineage": self.generates_lineage,
                "generates_governance_record": self.generates_governance_record,
                "enabled": self.enabled, "rationale": self.rationale,
                "control_version": self.control_version}


@dataclass(frozen=True)
class Page:
    id: str
    title: str
    sections: list = field(default_factory=list)
    visualizations: list = field(default_factory=list)
    controls: list = field(default_factory=list)        # list[InterventionControl]

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title,
            "sections": [s.to_dict() if isinstance(s, Section) else s for s in self.sections],
            "visualizations": [v.to_dict() if isinstance(v, Visualization) else v
                               for v in self.visualizations],
            "controls": [c.to_dict() if isinstance(c, InterventionControl) else c
                         for c in self.controls],
        }


@dataclass(frozen=True)
class NavArea:
    """A primary navigation area that owns one or more pages and carries context."""

    id: str
    title: str
    pages: list = field(default_factory=list)        # list[Page]
    context: dict = field(default_factory=dict)      # preserved navigation context

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "context": self.context,
            "pages": [p.to_dict() if isinstance(p, Page) else p for p in self.pages],
        }


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass
class ValidationReport:
    """The workstation's own validation report (stdlib only; no ml.validation)."""

    checks: list = field(default_factory=list)

    def add(self, name: str, passed: bool, detail: str = "") -> None:
        self.checks.append(CheckResult(name, bool(passed), detail))

    @property
    def ok(self) -> bool:
        return all(c.passed for c in self.checks)

    def failures(self) -> list:
        return [c for c in self.checks if not c.passed]

    def to_dict(self) -> dict:
        return {"ok": self.ok, "n_checks": len(self.checks),
                "n_failed": len(self.failures()),
                "checks": [c.to_dict() for c in self.checks]}


@dataclass
class WorkstationView:
    """The whole workstation view-model: ordered nav areas + validation + meta."""

    areas: list = field(default_factory=list)        # list[NavArea]
    validation: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "areas": [a.to_dict() if isinstance(a, NavArea) else a for a in self.areas],
            "validation": self.validation, "meta": self.meta,
        }

    def area(self, area_id: str) -> dict:
        for a in self.areas:
            ad = a.to_dict() if isinstance(a, NavArea) else a
            if ad["id"] == area_id:
                return ad
        raise KeyError(f"unknown nav area {area_id!r}")

    def all_controls(self) -> list:
        out = []
        for a in self.areas:
            ad = a.to_dict() if isinstance(a, NavArea) else a
            for page in ad["pages"]:
                out.extend(page.get("controls", []))
        return out
