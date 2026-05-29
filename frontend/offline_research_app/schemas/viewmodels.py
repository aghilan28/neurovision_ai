"""Typed view-model contracts for the research application.

Pure presentation data structures (stdlib only). A ``Section`` is a renderable
block (table / key-value / badges / text); a ``Visualization`` is a chart spec; a
``Page`` is a workflow view; an ``AppView`` is the whole application view-model.

The frontend has its **own** tiny ``ValidationReport`` (it must not import
``ml.validation`` or any domain module — NR-8).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..version import VIEWMODEL_VERSION


@dataclass(frozen=True)
class Section:
    kind: str          # "kv" | "table" | "badges" | "text"
    title: str
    data: dict
    viewmodel_version: str = VIEWMODEL_VERSION

    def to_dict(self) -> dict:
        return {"kind": self.kind, "title": self.title, "data": self.data,
                "viewmodel_version": self.viewmodel_version}


@dataclass(frozen=True)
class Visualization:
    type: str          # "bar" | "line" | "graph" | "layout" | "table"
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
class CheckResult:
    name: str
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass
class ValidationReport:
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
class AppView:
    pages: list = field(default_factory=list)   # list[Page]
    validation: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "pages": [p.to_dict() if isinstance(p, Page) else p for p in self.pages],
            "validation": self.validation,
            "meta": self.meta,
        }
