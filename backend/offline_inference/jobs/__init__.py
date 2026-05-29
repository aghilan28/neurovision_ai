"""``backend/offline_inference/jobs`` — the job system (V1-P7).

Versioned, traceable, recoverable, auditable units of work:
  * ``InferenceJob``  — run the full orchestrator for one config.
  * ``BatchJob``      — run many inference configs; recoverable (skips completed).
  * ``ValidationJob`` — (re)validate a persisted run's artifacts/integrity.
  * ``AuditJob``      — collect the audit record / lineage chain for a run.
  * ``ArtifactJob``   — verify artifact integrity of a persisted run directory.
  * ``ReportJob``     — collect/verify the registered reports for a run.

``JobRunner`` executes jobs, records results, and supports retry/recovery.
"""

from __future__ import annotations

from .jobs import (
    JobStatus, JobResult, Job,
    InferenceJob, BatchJob, ValidationJob, AuditJob, ArtifactJob, ReportJob,
    JobRunner,
)

__all__ = [
    "JobStatus", "JobResult", "Job",
    "InferenceJob", "BatchJob", "ValidationJob", "AuditJob", "ArtifactJob", "ReportJob",
    "JobRunner",
]
