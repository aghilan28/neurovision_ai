"""``backend/offline_inference`` — Offline Inference Platform (V1-P7).

The orchestration layer that connects every Version 1 subsystem into a single
deterministic, offline workflow: **raw EEG → intelligence output**, with every
stage versioned, traceable, and independently auditable.

Offline-only by construction: no APIs, no networking, no multi-user, no real-time,
no clinical deployment (those are V2+, recorded in ``.gcc/decisions/ADR-0002``).

Public surface:
  * ``PipelineConfig``        — pinned, content-addressed run configuration.
  * ``InferenceOrchestrator`` — the 15-stage master orchestrator.
  * ``JobRunner`` + jobs      — versioned, recoverable, auditable units of work.
  * registries / artifacts / lineage / validation / reports / schemas.
"""

from __future__ import annotations

from .version import (
    OFFLINE_INFERENCE_VERSION, PIPELINE_VERSION, ORCHESTRATOR_VERSION,
    EXECUTION_ENGINE_VERSION, JOB_SYSTEM_VERSION, INFERENCE_REGISTRY_VERSION,
    OUTPUT_CONTRACT_VERSION, INFERENCE_ARTIFACT_VERSION, INFERENCE_LINEAGE_VERSION,
    INFERENCE_REPORT_VERSION,
)
from .pipelines import PipelineConfig
from .orchestrator import InferenceOrchestrator, OrchestratorResult
from .execution import ExecutionEngine, ExecutionStatus, Stage, ExecutionResult, RealClock, FakeClock
from .registry import InferenceRegistry, InferenceRecord
from .artifacts import InferenceArtifactStore
from .validation import InferenceValidator, InferenceValidationError
from .jobs import (
    JobRunner, JobStatus, JobResult,
    InferenceJob, BatchJob, ValidationJob, AuditJob, ArtifactJob, ReportJob,
)

__all__ = [
    "OFFLINE_INFERENCE_VERSION", "PIPELINE_VERSION", "ORCHESTRATOR_VERSION",
    "EXECUTION_ENGINE_VERSION", "JOB_SYSTEM_VERSION", "INFERENCE_REGISTRY_VERSION",
    "OUTPUT_CONTRACT_VERSION", "INFERENCE_ARTIFACT_VERSION", "INFERENCE_LINEAGE_VERSION",
    "INFERENCE_REPORT_VERSION",
    "PipelineConfig", "InferenceOrchestrator", "OrchestratorResult",
    "ExecutionEngine", "ExecutionStatus", "Stage", "ExecutionResult", "RealClock", "FakeClock",
    "InferenceRegistry", "InferenceRecord", "InferenceArtifactStore",
    "InferenceValidator", "InferenceValidationError",
    "JobRunner", "JobStatus", "JobResult",
    "InferenceJob", "BatchJob", "ValidationJob", "AuditJob", "ArtifactJob", "ReportJob",
]
