"""Version identities for the Clinical Case Foundation (V2-P1).

Every clinical-case artifact (entity, registry record, lifecycle transition, audit
event, lineage node, report) records the exact versions that produced it, so a Case
is reproducible and auditable for its entire (permanent) lifetime (AP-5/AP-6/AP-9,
NR-10/NR-11). Bump a version when the named behaviour or contract changes.
"""

from __future__ import annotations

# The clinical-case subsystem as a whole.
CLINICAL_CASES_VERSION: str = "clinical-cases@1.0.0"

# Component versions.
CASE_DOMAIN_VERSION: str = "case-domain@1.0.0"
CASE_IDENTITY_VERSION: str = "case-identity@1.0.0"
CASE_LIFECYCLE_VERSION: str = "case-lifecycle@1.0.0"
CASE_REGISTRY_VERSION: str = "case-registry@1.0.0"
CASE_AUDIT_VERSION: str = "case-audit@1.0.0"
CASE_LINEAGE_VERSION: str = "case-lineage@1.0.0"
CASE_VALIDATION_VERSION: str = "case-validation@1.0.0"
CASE_REPORT_VERSION: str = "case-report@1.0.0"

# A fixed, deterministic default timestamp used wherever a "created_at" must NOT
# perturb reproducibility hashes. Real wall-clock time, where audit needs it, is
# recorded as NON-hashed metadata only (mirrors ml.version.DETERMINISTIC_EPOCH).
DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
