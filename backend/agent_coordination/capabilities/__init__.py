"""Agent capability analysis package (V4-P5)."""

from __future__ import annotations

from .capabilities import (
    usable_capabilities, satisfies, unmet_dependencies, high_risk_unapproved,
    requires_capability_approval, capability_summary,
)

__all__ = [
    "usable_capabilities", "satisfies", "unmet_dependencies", "high_risk_unapproved",
    "requires_capability_approval", "capability_summary",
]
