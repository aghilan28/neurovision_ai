"""Typed view-model contracts for the Clinical Workstation.

Pure presentation data structures (stdlib only — NR-8). These mirror the research
app's view-models and add ``NavArea`` (a primary navigation area that owns one or
more pages) so the workstation can present a single, coherent operational
environment over every Version 2 subsystem.

* ``Section``        — a renderable block (kv / table / badges / text).
* ``Visualization``  — a chart spec (bar / line / graph / layout / timeline / table).
* ``Page``           — one workspace view (sections + visualizations).
* ``NavArea``        — a primary navigation area (id, title, pages, context keys).
* ``WorkstationView``— the whole application view-model (nav + pages + validation).
* ``ValidationReport`` — the frontend's OWN tiny report (never imports ml.validation).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..version import WORKSTATION_VIEWMODEL_VERSION


@dataclass(frozen=True)
class Section:
    kind: str          # "kv" | "table" | "badges" | "text"
    title: str
    data: dict
    viewmodel_version: str = WORKSTATION_VIEWMODEL_VERSION

    def to_dict(self) -> dict:
        return {"kind": self.kind, "title": self.title, "data": self.data,
                "viewmodel_version": self.viewmodel_version}


@dataclass(frozen=True)
class Visualization:
    type: str          # "bar" | "line" | "graph" | "layout" | "timeline" | "table"
    title: str
    spec: dict

    def to_dict(self) -> dict:
        return {"type": self.type, "title": self.title, "spec": self.spec}


@dataclass(frozen=True)
class Page:
    id: str
    title: str
    sections: list = field(default_factory=list)
    visualizations: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "sections": [s.to_dict() if isinstance(s, Section) else s for s in self.sections],
            "visualizations": [v.to_dict() if isinstance(v, Visualization) else v
                               for v in self.visualizations],
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
            "id": self.id,
            "title": self.title,
            "context": self.context,
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
            "validation": self.validation,
            "meta": self.meta,
        }

    def area(self, area_id: str) -> dict:
        for a in self.areas:
            ad = a.to_dict() if isinstance(a, NavArea) else a
            if ad["id"] == area_id:
                return ad
        raise KeyError(f"unknown nav area {area_id!r}")
