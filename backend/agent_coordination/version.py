"""Version identities for the Agent Coordination Framework (V4-P5).

Every agent artifact records the versions that produced it, so it is reproducible
and auditable for its whole lifetime (AP-5/AP-6/AP-9, NR-10/NR-11).

An **Agent** is a first-class *governed participant* — a description of who/what can
perform work, with declared capabilities and assignments. Agents are **not**
autonomous systems, self-modifying systems, or unbounded executors. They describe
capability; they do not possess autonomous authority. Agents are computed and
governed deterministically (no wall-clock); an agent only becomes AVAILABLE through
policy-governed approval (V4-P2 integration), and every assignment must satisfy the
target's capability requirements without implying execution.
"""

from __future__ import annotations

AGENT_COORDINATION_VERSION: str = "agent-coordination@1.0.0"

AGENT_DOMAIN_VERSION: str = "agent-domain@1.0.0"
AGENT_IDENTITY_VERSION: str = "agent-identity@1.0.0"
AGENT_TAXONOMY_VERSION: str = "agent-taxonomy@1.0.0"
AGENT_CAPABILITY_VERSION: str = "agent-capability@1.0.0"
AGENT_ASSIGNMENT_VERSION: str = "agent-assignment@1.0.0"
AGENT_LIFECYCLE_VERSION: str = "agent-lifecycle@1.0.0"
AGENT_RELATIONSHIP_VERSION: str = "agent-relationship@1.0.0"
AGENT_GOVERNANCE_VERSION: str = "agent-governance@1.0.0"
AGENT_REGISTRY_VERSION: str = "agent-registry@1.0.0"
AGENT_AUDIT_VERSION: str = "agent-audit@1.0.0"
AGENT_LINEAGE_VERSION: str = "agent-lineage@1.0.0"
AGENT_VALIDATION_VERSION: str = "agent-validation@1.0.0"
AGENT_REPORT_VERSION: str = "agent-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
