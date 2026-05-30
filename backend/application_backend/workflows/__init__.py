"""``backend/application_backend/workflows`` — EEG application workflow (P6-E).

Orchestrates the reused P1-P5 services (upload -> validate -> process -> features ->
predict -> confidence -> explanation) without duplicating any business logic.
"""

from __future__ import annotations

from .eeg_workflow import EegWorkflowService, ModelContext, WorkflowOutcome, WorkflowError

__all__ = ["EegWorkflowService", "ModelContext", "WorkflowOutcome", "WorkflowError"]
