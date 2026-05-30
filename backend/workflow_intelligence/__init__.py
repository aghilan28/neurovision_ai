"""``backend/workflow_intelligence`` — Workflow Intelligence Layer (V3-P3).

Teaches the platform to understand **workflows**: work, flow, progression,
transitions, dependencies, bottlenecks, efficiency, and operational behavior. The
workflow itself is a **first-class entity**.

Every workflow is derived strictly **from events (V3-P1) and temporal intelligence
(V3-P2)** — no hidden workflow state. It is versioned, traceable, auditable,
lineage-tracked, deterministic, and governed. Its lineage parents are the **event**
(and optionally **timeline**) nodes it derives from, so ``verify_chain`` spans
Patient → ... → Event → (Timeline) → Workflow. Shares the platform's single
``ml.lineage.LineageTracker`` and the shared ``ImmutableAuditLog``; it creates no
parallel lineage/audit system.

Engines: transitions (state changes from lifecycle events), dependencies (upstream/
downstream/blocked/waiting/completed between entities), bottlenecks (slow
transitions, rework, stalls, wait states, dependency congestion), and efficiency
(completion rate, transition durations in *logical steps*, rework rate, throughput,
operational velocity, workflow health score).

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` and the
sibling V3 subsystems it derives from; never imports ``frontend``. Scope is strictly
V3-P3 — no operational analytics layer/recommendations/dashboards, no realtime, no
FHIR/HL7/EMR, no V4. See ``.gcc/decisions/ADR-0008``.
"""

from __future__ import annotations

from .version import (
    WORKFLOW_INTELLIGENCE_VERSION, WORKFLOW_DOMAIN_VERSION, WORKFLOW_IDENTITY_VERSION,
    WORKFLOW_TRANSITION_VERSION, WORKFLOW_DEPENDENCY_VERSION, WORKFLOW_METRIC_VERSION,
    WORKFLOW_REGISTRY_VERSION, WORKFLOW_AUDIT_VERSION, WORKFLOW_LINEAGE_VERSION,
    WORKFLOW_VALIDATION_VERSION, WORKFLOW_REPORT_VERSION,
)
from .identity import WorkflowIdentity, WorkflowIdentityError, mint_workflow, validate_identity
from .models import (
    WorkflowTransition, WorkflowDependency, WorkflowMetric, WorkflowMetadata, WorkflowRecord,
    WorkflowAuditRecord, WorkflowVersion, WorkflowLineageRecord, WorkflowRegistryRecord,
)
from .dependencies import EntityRef, derive_dependencies
from .transitions import derive_transitions, transition_frequencies
from .analytics import WorkflowBuilder
from .audit import make_workflow_audit_log
from .registry import WorkflowRegistry
from .validation import WorkflowGovernanceGate, WorkflowValidator, WorkflowValidationError
from .service import WorkflowIntelligenceService

__all__ = [
    "WORKFLOW_INTELLIGENCE_VERSION", "WORKFLOW_DOMAIN_VERSION", "WORKFLOW_IDENTITY_VERSION",
    "WORKFLOW_TRANSITION_VERSION", "WORKFLOW_DEPENDENCY_VERSION", "WORKFLOW_METRIC_VERSION",
    "WORKFLOW_REGISTRY_VERSION", "WORKFLOW_AUDIT_VERSION", "WORKFLOW_LINEAGE_VERSION",
    "WORKFLOW_VALIDATION_VERSION", "WORKFLOW_REPORT_VERSION",
    "WorkflowIdentity", "WorkflowIdentityError", "mint_workflow", "validate_identity",
    "WorkflowTransition", "WorkflowDependency", "WorkflowMetric", "WorkflowMetadata",
    "WorkflowRecord", "WorkflowAuditRecord", "WorkflowVersion", "WorkflowLineageRecord",
    "WorkflowRegistryRecord",
    "EntityRef", "derive_dependencies", "derive_transitions", "transition_frequencies",
    "WorkflowBuilder", "make_workflow_audit_log", "WorkflowRegistry",
    "WorkflowGovernanceGate", "WorkflowValidator", "WorkflowValidationError",
    "WorkflowIntelligenceService",
]
