"""Event lifecycle (V3-P1).

Events have a deliberately tiny lifecycle: an event is born ``active`` and may
only ever transition to ``superseded``. There is no ``edit`` and no return path —
facts are permanent. Supersession is modeled as a *new* event plus a governed
status flip on the old one (handled by the service + registry), never a rewrite.
"""

from __future__ import annotations

from ..version import EVENT_LIFECYCLE_VERSION

ACTIVE = "active"
SUPERSEDED = "superseded"

# The only permitted transition.
_TRANSITIONS = {ACTIVE: frozenset({SUPERSEDED}), SUPERSEDED: frozenset()}


class EventLifecycleError(RuntimeError):
    """Raised on an illegal event status transition."""


def can_transition(src: str, dst: str) -> bool:
    return dst in _TRANSITIONS.get(src, frozenset())


def check_transition(src: str, dst: str) -> None:
    if not can_transition(src, dst):
        raise EventLifecycleError(
            f"forbidden event transition {src} -> {dst} "
            f"(allowed: {sorted(_TRANSITIONS.get(src, frozenset()))})")


def to_dict() -> dict:
    return {"event_lifecycle_version": EVENT_LIFECYCLE_VERSION,
            "states": [ACTIVE, SUPERSEDED],
            "transitions": {k: sorted(v) for k, v in _TRANSITIONS.items()}}
