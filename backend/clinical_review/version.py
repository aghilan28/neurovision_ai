"""Version identities for the Clinical Review Workflow (V2-P2).

Every review artifact (entity, session, assignment, lifecycle transition, audit
event, lineage node, report) records the versions that produced it, so a review is
reproducible and auditable for its whole lifetime (AP-5/AP-6/AP-9, NR-10/NR-11).
"""

from __future__ import annotations

CLINICAL_REVIEW_VERSION: str = "clinical-review@1.0.0"

REVIEW_DOMAIN_VERSION: str = "review-domain@1.0.0"
REVIEW_IDENTITY_VERSION: str = "review-identity@1.0.0"
REVIEW_WORKFLOW_VERSION: str = "review-workflow@1.0.0"
REVIEW_SESSION_VERSION: str = "review-session@1.0.0"
REVIEW_ASSIGNMENT_VERSION: str = "review-assignment@1.0.0"
REVIEW_TRACKING_VERSION: str = "review-tracking@1.0.0"
REVIEW_REGISTRY_VERSION: str = "review-registry@1.0.0"
REVIEW_AUDIT_VERSION: str = "review-audit@1.0.0"
REVIEW_LINEAGE_VERSION: str = "review-lineage@1.0.0"
REVIEW_VALIDATION_VERSION: str = "review-validation@1.0.0"
REVIEW_REPORT_VERSION: str = "review-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
