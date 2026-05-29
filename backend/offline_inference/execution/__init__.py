"""``backend/offline_inference/execution`` — deterministic execution engine (V1-P7).

Runs an ordered list of versioned stages against a shared context, recording per-
stage status, timing, and output signatures, with explicit failure and recovery
(resume) states. Timing is wall-clock and recorded as NON-hashed metadata; the
content signature excludes it so reproducibility is unaffected (NR-10).
"""

from __future__ import annotations

from .engine import (
    ExecutionStatus,
    Stage,
    StageResult,
    ExecutionResult,
    ExecutionEngine,
    Clock,
    RealClock,
    FakeClock,
)

__all__ = [
    "ExecutionStatus",
    "Stage",
    "StageResult",
    "ExecutionResult",
    "ExecutionEngine",
    "Clock",
    "RealClock",
    "FakeClock",
]
