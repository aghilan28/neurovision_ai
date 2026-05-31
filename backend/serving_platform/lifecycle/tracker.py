"""Serving execution lifecycle tracker (DRP3-F).

Records the ordered lifecycle transitions of one serving execution and validates that they
follow the canonical order:

    request_created -> request_validated -> model_selected -> inference_executed ->
    response_generated -> response_delivered -> execution_completed

A rejected request stops the lifecycle early (e.g. after ``request_created`` /
``request_validated``); the tracker records exactly the states that occurred and the final
state. Deterministic; no wall-clock.
"""

from __future__ import annotations

from ..models.domain import LIFECYCLE_ORDER, LifecycleState, ServingLifecycleRecord


class LifecycleError(RuntimeError):
    """Raised on an out-of-order lifecycle transition (a programmer error)."""


class LifecycleTracker:
    """Accumulates ordered lifecycle transitions for one request."""

    def __init__(self, request_id: str):
        self.request_id = request_id
        self._transitions: list[tuple] = []

    def record(self, state: LifecycleState, detail: str = "") -> "LifecycleTracker":
        idx = LIFECYCLE_ORDER.index(state)
        if self._transitions:
            last_idx = LIFECYCLE_ORDER.index(LifecycleState(self._transitions[-1][0]))
            if idx <= last_idx:
                raise LifecycleError(
                    f"out-of-order transition {state.value!r} after {self._transitions[-1][0]!r}")
        self._transitions.append((state.value, detail))
        return self

    @property
    def current(self) -> str:
        return self._transitions[-1][0] if self._transitions else ""

    def to_record(self) -> ServingLifecycleRecord:
        return ServingLifecycleRecord(
            request_id=self.request_id, transitions=tuple(self._transitions),
            final_state=self.current)


__all__ = ["LifecycleTracker", "LifecycleError"]
