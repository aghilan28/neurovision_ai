"""``operations/logging`` — structured logging foundation (P8-F).

Deterministic, machine-readable (JSON) structured logging with record builders for
requests, workflows, predictions, and errors, plus audit/trace correlation. This does
not replace or modify any backend/frontend behaviour — it is an operational sink that
*records* operational events in a uniform, parseable shape.

Determinism: each record carries a monotonic logical ``seq`` and a ``ts`` from an
injectable clock (default: a fixed deterministic epoch, so tests/verification are
reproducible). A real deployment injects a wall-clock. No randomness anywhere.

NB: this is the package ``operations.logging``; modules elsewhere that ``import logging``
still get the standard library (absolute import).
"""

from __future__ import annotations

import sys
from typing import Callable, Optional

from ..util import canonical_json
from ..version import DETERMINISTIC_EPOCH, OPERATIONS_LOGGING_VERSION

_LEVELS = {"debug": 10, "info": 20, "warning": 30, "error": 40, "critical": 50}


def _deterministic_clock() -> str:
    return DETERMINISTIC_EPOCH


class BufferSink:
    """Collects log lines in memory (testable, deterministic)."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, line: str) -> None:
        self.lines.append(line)

    def records(self) -> list[dict]:
        import json
        return [json.loads(line) for line in self.lines]


class StreamSink:
    """Writes log lines to a stream (default stdout) — for container deployments."""

    def __init__(self, stream=None) -> None:
        self._stream = stream or sys.stdout

    def __call__(self, line: str) -> None:
        self._stream.write(line + "\n")
        self._stream.flush()


class StructuredLogger:
    """Emits structured JSON log records, filtered by level."""

    def __init__(self, name: str = "neurovision", *, sink: Optional[Callable] = None,
                 min_level: str = "info", clock: Optional[Callable] = None):
        self.name = name
        self.sink = sink if sink is not None else BufferSink()
        self.min_level = min_level
        self._clock = clock or _deterministic_clock
        self._seq = 0

    def _emit(self, level: str, event: str, fields: dict) -> dict:
        self._seq += 1
        record = {
            "logger": self.name, "level": level, "event": event,
            "seq": self._seq, "ts": self._clock(),
            "logging_version": OPERATIONS_LOGGING_VERSION,
            **{k: v for k, v in fields.items() if v is not None},
        }
        if _LEVELS.get(level, 0) >= _LEVELS.get(self.min_level, 20):
            self.sink(canonical_json(record))
        return record

    def log(self, level: str, event: str, **fields) -> dict:
        return self._emit(level, event, fields)

    def debug(self, event, **f):
        return self._emit("debug", event, f)

    def info(self, event, **f):
        return self._emit("info", event, f)

    def warning(self, event, **f):
        return self._emit("warning", event, f)

    def error(self, event, **f):
        return self._emit("error", event, f)

    # --- domain record builders (correlate to the backend's audit/lineage) ----
    def request(self, *, request_id: str, operation: str, status: str,
                user_id: Optional[str] = None, session_id: Optional[str] = None,
                trace_id: Optional[str] = None) -> dict:
        return self._emit("info", "api_request", {
            "kind": "request", "request_id": request_id, "operation": operation,
            "status": status, "user_id": user_id, "session_id": session_id, "trace_id": trace_id})

    def workflow(self, *, workflow_id: str, stage: str, status: str,
                 lineage_id: Optional[str] = None, audit_head: Optional[str] = None) -> dict:
        return self._emit("info", "workflow_stage", {
            "kind": "workflow", "workflow_id": workflow_id, "stage": stage, "status": status,
            "lineage_id": lineage_id, "audit_head": audit_head})

    def prediction(self, *, prediction_id: str, predicted_label: str, confidence_level: str,
                   calibration_quality: Optional[str] = None,
                   lineage_id: Optional[str] = None) -> dict:
        return self._emit("info", "prediction_generated", {
            "kind": "prediction", "prediction_id": prediction_id,
            "predicted_label": predicted_label, "confidence_level": confidence_level,
            "calibration_quality": calibration_quality, "lineage_id": lineage_id})

    def failure(self, *, error_type: str, message: str, where: str,
                trace_id: Optional[str] = None) -> dict:
        return self._emit("error", "error", {
            "kind": "error", "error_type": error_type, "message": message, "where": where,
            "trace_id": trace_id})


def build_logging_report(logger: StructuredLogger) -> dict:
    sink = logger.sink
    records = sink.records() if isinstance(sink, BufferSink) else []
    kinds: dict = {}
    levels: dict = {}
    for r in records:
        kinds[r.get("kind", r.get("event"))] = kinds.get(r.get("kind", r.get("event")), 0) + 1
        levels[r["level"]] = levels.get(r["level"], 0) + 1
    return {
        "report_type": "logging", "logging_version": OPERATIONS_LOGGING_VERSION,
        "format": "json", "machine_readable": True, "deterministic": True,
        "n_records": len(records), "by_kind": kinds, "by_level": levels,
    }


__all__ = [
    "StructuredLogger", "BufferSink", "StreamSink", "build_logging_report",
]
