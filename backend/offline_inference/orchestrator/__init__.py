"""``backend/offline_inference/orchestrator`` — the master orchestrator (V1-P7).

Connects every Version 1 subsystem into one deterministic, staged workflow:

    Dataset Ingestion → Validation → Preprocessing → Dataset Intelligence →
    Evaluation Preparation → Model Selection → Inference → Calibration →
    Conformal Prediction → Coverage Validation → Risk Assessment →
    Output Generation → Artifact Registration → Lineage Registration → Audit Generation

Every stage is versioned, traceable, and independently auditable. Raw EEG in,
intelligence output out — with full provenance.
"""

from __future__ import annotations

from .orchestrator import InferenceOrchestrator, OrchestratorResult

__all__ = ["InferenceOrchestrator", "OrchestratorResult"]
