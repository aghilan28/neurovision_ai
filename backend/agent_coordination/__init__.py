"""``backend/agent_coordination`` — Agent Coordination Framework (V4-P5).

Introduces **Agents as first-class governed entities** — descriptions of who/what
can perform work (human / system / service / future-AI participants), with declared
**capabilities** and **assignments**. Agents are **not** autonomous systems,
self-modifying systems, or unbounded executors: they describe capability and hold no
autonomous authority. They answer "*who can perform work?*".

Every agent is versioned, traceable, auditable, lineage-tracked, governed,
deterministic, and recoverable. An agent moves through a governed lifecycle (PROPOSED
-> DRAFT -> UNDER_REVIEW -> APPROVED -> AVAILABLE -> {SUSPENDED, RETIRED} ->
ARCHIVED); forbidden transitions are blocked, and an agent cannot become AVAILABLE
without policy-governed approval (V4-P2 integration) and capability approval for any
high/critical-risk capability. Every **assignment** (Agent -> Task/Plan/Goal/Policy)
must satisfy the target's capability requirements and **never implies execution**.
Shares the platform's single ``ml.lineage.LineageTracker`` and the shared
``ImmutableAuditLog`` — no parallel lineage/audit/governance.

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` and
sibling ``backend`` subsystems; never imports ``frontend``. Scope is strictly V4-P5
— no autonomous/self-modifying agents, no execution. See ``.gcc/decisions/ADR-0013``.
"""

from __future__ import annotations

from .version import (
    AGENT_COORDINATION_VERSION, AGENT_DOMAIN_VERSION, AGENT_IDENTITY_VERSION,
    AGENT_TAXONOMY_VERSION, AGENT_CAPABILITY_VERSION, AGENT_ASSIGNMENT_VERSION,
    AGENT_LIFECYCLE_VERSION, AGENT_RELATIONSHIP_VERSION, AGENT_GOVERNANCE_VERSION,
    AGENT_REGISTRY_VERSION, AGENT_AUDIT_VERSION, AGENT_LINEAGE_VERSION,
    AGENT_VALIDATION_VERSION, AGENT_REPORT_VERSION,
)
from .identity import (
    AgentIdentity, AgentIdentityError, mint_agent, mint_relationship, mint_assignment,
    validate_identity, validate_relationship_identity, validate_assignment_identity,
)
from .taxonomy import (
    AgentCategory, AgentPriority, AgentRelationType, CapabilityRisk, CapabilityMode,
    AssignmentState, TaxonomyError, AGENT_CATEGORIES, AGENT_PRIORITIES, AGENT_RELATION_TYPES,
    CAPABILITY_RISK_LEVELS, CAPABILITY_MODES, ASSIGNMENT_STATES, ASSIGNMENT_TARGET_KINDS,
    is_category, validate_category, parent_of, ancestry, is_priority, priority_rank,
    is_relation, validate_relation,
)
from .lifecycle import (
    AgentLifecycleState, AgentLifecycle, AgentLifecycleError, AgentTransitionRecord,
    AGENT_TRANSITIONS, GOVERNED_TRANSITIONS,
)
from .models import (
    AgentMetadata, AgentCapability, AgentAssignment, AgentConstraintReference, AgentVersion,
    AgentAuditRecord, AgentRelationship, AgentGovernanceRecord, AgentLineageRecord,
    AgentRegistryRecord, AgentRecord,
)
from .capabilities import satisfies, usable_capabilities, capability_summary
from .governance import AgentGovernanceGate, AgentGovernanceError
from .registry import AgentRegistry
from .validation import AgentValidator
from .audit import make_agent_audit_log
from .service import AgentService, AgentCapabilityError

__all__ = [
    "AGENT_COORDINATION_VERSION", "AGENT_DOMAIN_VERSION", "AGENT_IDENTITY_VERSION",
    "AGENT_TAXONOMY_VERSION", "AGENT_CAPABILITY_VERSION", "AGENT_ASSIGNMENT_VERSION",
    "AGENT_LIFECYCLE_VERSION", "AGENT_RELATIONSHIP_VERSION", "AGENT_GOVERNANCE_VERSION",
    "AGENT_REGISTRY_VERSION", "AGENT_AUDIT_VERSION", "AGENT_LINEAGE_VERSION",
    "AGENT_VALIDATION_VERSION", "AGENT_REPORT_VERSION",
    "AgentIdentity", "AgentIdentityError", "mint_agent", "mint_relationship", "mint_assignment",
    "validate_identity", "validate_relationship_identity", "validate_assignment_identity",
    "AgentCategory", "AgentPriority", "AgentRelationType", "CapabilityRisk", "CapabilityMode",
    "AssignmentState", "TaxonomyError", "AGENT_CATEGORIES", "AGENT_PRIORITIES",
    "AGENT_RELATION_TYPES", "CAPABILITY_RISK_LEVELS", "CAPABILITY_MODES", "ASSIGNMENT_STATES",
    "ASSIGNMENT_TARGET_KINDS", "is_category", "validate_category", "parent_of", "ancestry",
    "is_priority", "priority_rank", "is_relation", "validate_relation",
    "AgentLifecycleState", "AgentLifecycle", "AgentLifecycleError", "AgentTransitionRecord",
    "AGENT_TRANSITIONS", "GOVERNED_TRANSITIONS",
    "AgentMetadata", "AgentCapability", "AgentAssignment", "AgentConstraintReference",
    "AgentVersion", "AgentAuditRecord", "AgentRelationship", "AgentGovernanceRecord",
    "AgentLineageRecord", "AgentRegistryRecord", "AgentRecord",
    "satisfies", "usable_capabilities", "capability_summary",
    "AgentGovernanceGate", "AgentGovernanceError", "AgentRegistry", "AgentValidator",
    "make_agent_audit_log", "AgentService", "AgentCapabilityError",
]
