"""The deterministic execution engine.

A ``Stage`` is a named, versioned step with a ``run(context) -> record`` callable
that mutates a shared mutable ``context`` and returns a record dict containing at
least a content ``signature``. The ``ExecutionEngine`` runs stages in order,
capturing status/timing/signature per stage and stopping at the first failure with
a recoverable state. ``execute(..., skip=...)`` resumes by skipping already-
completed stages (marked ``RECOVERED``), reusing the retained context.

Determinism: stage *content* signatures and the execution *content signature*
exclude timing. Wall-clock durations/timestamps are recorded only as non-hashed
metadata (NR-9/NR-10).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, Protocol

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import EXECUTION_ENGINE_VERSION, DETERMINISTIC_EPOCH


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    RECOVERED = "recovered"


class Clock(Protocol):
    def now(self) -> float: ...
    def timestamp(self) -> str: ...


class RealClock:
    """Monotonic durations + a fixed deterministic content timestamp.

    ``now()`` uses a monotonic counter for *durations* (non-hashed metadata).
    ``timestamp()`` returns the deterministic epoch so nothing time-derived leaks
    into content; wall-clock recording, if ever needed, is an explicit opt-in.
    """

    def now(self) -> float:
        return time.perf_counter()

    def timestamp(self) -> str:
        return DETERMINISTIC_EPOCH


class FakeClock:
    """Deterministic clock for tests: increments by a fixed step per call."""

    def __init__(self, step: float = 0.001):
        self._t = 0.0
        self._step = step

    def now(self) -> float:
        self._t += self._step
        return self._t

    def timestamp(self) -> str:
        return DETERMINISTIC_EPOCH


@dataclass(frozen=True)
class Stage:
    name: str
    version: str
    run: Callable[[dict], dict]


@dataclass
class StageResult:
    name: str
    version: str
    status: ExecutionStatus
    duration_s: float
    output_signature: Optional[str]
    error: Optional[str] = None
    attempt: int = 1

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "status": self.status.value,
            "duration_s": round(float(self.duration_s), 6),  # non-hashed metadata
            "output_signature": self.output_signature,
            "error": self.error,
            "attempt": self.attempt,
        }


@dataclass
class ExecutionResult:
    pipeline_version: str
    stages: list[StageResult] = field(default_factory=list)
    status: ExecutionStatus = ExecutionStatus.PENDING
    failed_stage: Optional[str] = None
    total_duration_s: float = 0.0
    recovered: bool = False
    engine_version: str = EXECUTION_ENGINE_VERSION

    @property
    def ok(self) -> bool:
        return self.status == ExecutionStatus.SUCCEEDED

    def succeeded_stage_names(self) -> set[str]:
        return {s.name for s in self.stages
                if s.status in (ExecutionStatus.SUCCEEDED, ExecutionStatus.RECOVERED)}

    def content_signature(self) -> str:
        """Hash over (pipeline, stage name/version/status/output_signature) — no timing."""
        return hash_obj({
            "pipeline_version": self.pipeline_version,
            "engine_version": self.engine_version,
            "stages": [(s.name, s.version, s.status.value, s.output_signature) for s in self.stages],
        })

    def to_dict(self) -> dict:
        return {
            "engine_version": self.engine_version,
            "pipeline_version": self.pipeline_version,
            "status": self.status.value,
            "failed_stage": self.failed_stage,
            "recovered": self.recovered,
            "total_duration_s": round(float(self.total_duration_s), 6),  # non-hashed
            "n_stages": len(self.stages),
            "stages": [s.to_dict() for s in self.stages],
            "content_signature": self.content_signature(),
        }


class ExecutionEngine:
    """Runs stages with status/timing capture, failure stop, and recovery resume."""

    def __init__(self, pipeline_version: str, clock: Optional[Clock] = None):
        self.pipeline_version = pipeline_version
        self.clock = clock or RealClock()

    def execute(self, stages: list[Stage], context: dict,
                skip: frozenset[str] = frozenset()) -> ExecutionResult:
        result = ExecutionResult(pipeline_version=self.pipeline_version)
        total = 0.0
        for stage in stages:
            if stage.name in skip:
                # already completed in a prior (failed) run; resume past it
                result.stages.append(StageResult(
                    stage.name, stage.version, ExecutionStatus.RECOVERED, 0.0,
                    context.get("_stage_signatures", {}).get(stage.name), attempt=2))
                result.recovered = True
                continue
            t0 = self.clock.now()
            try:
                record = stage.run(context)
                dur = self.clock.now() - t0
                total += dur
                sig = record.get("signature") if isinstance(record, dict) else None
                context.setdefault("_stage_signatures", {})[stage.name] = sig
                context.setdefault("_stage_records", {})[stage.name] = record
                result.stages.append(StageResult(
                    stage.name, stage.version, ExecutionStatus.SUCCEEDED, dur, sig))
            except Exception as exc:  # capture failure state; remain recoverable
                dur = self.clock.now() - t0
                total += dur
                result.stages.append(StageResult(
                    stage.name, stage.version, ExecutionStatus.FAILED, dur, None, repr(exc)))
                result.status = ExecutionStatus.FAILED
                result.failed_stage = stage.name
                result.total_duration_s = total
                return result
        result.status = ExecutionStatus.SUCCEEDED
        result.total_duration_s = total
        return result
