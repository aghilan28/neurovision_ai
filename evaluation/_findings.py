"""Shared finding/severity primitives for the whole ``evaluation/`` package.

A single source of truth used by both the Dataset Intelligence Layer (V1-P3) and
the Evaluation Foundation (V1-P4), so a "finding" means the same thing everywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    """Severity of a structured finding (report-only; never mutates data)."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class Finding:
    """A single structured finding (quality, leakage, validation, etc.)."""

    code: str
    severity: Severity
    message: str
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Finding:
        return cls(
            code=data["code"],
            severity=Severity(data["severity"]),
            message=data["message"],
            context=dict(data.get("context", {})),
        )
