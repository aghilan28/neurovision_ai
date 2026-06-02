"""Version identities for the Findings & Interpretation Layer (V2-P3).

Every finding artifact (entity, evidence link, interpretation, lifecycle
transition, audit event, lineage node, report) records the versions that produced
it, so a Finding is reproducible and auditable for its whole lifetime
(AP-5/AP-6/AP-9, NR-10/NR-11).
"""

from __future__ import annotations

CLINICAL_FINDINGS_VERSION: str = "clinical-findings@1.0.0"

FINDING_DOMAIN_VERSION: str = "finding-domain@1.0.0"
FINDING_IDENTITY_VERSION: str = "finding-identity@1.0.0"
FINDING_LIFECYCLE_VERSION: str = "finding-lifecycle@1.0.0"
FINDING_EVIDENCE_VERSION: str = "finding-evidence@1.0.0"
FINDING_INTERPRETATION_VERSION: str = "finding-interpretation@1.0.0"
FINDING_REGISTRY_VERSION: str = "finding-registry@1.0.0"
FINDING_AUDIT_VERSION: str = "finding-audit@1.0.0"
FINDING_LINEAGE_VERSION: str = "finding-lineage@1.0.0"
FINDING_VALIDATION_VERSION: str = "finding-validation@1.0.0"
FINDING_REPORT_VERSION: str = "finding-report@1.0.0"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
