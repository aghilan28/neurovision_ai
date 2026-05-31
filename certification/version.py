"""Version identities for the Deployment Readiness & Production Certification Program (P10).

Certification is the top-level *certification* layer (peer of ``scripts``/``operations``/
``validation``): it audits the existing P1-P9 systems and produces an evidence-based
deployment decision. It modifies nothing. Every certification artifact records the versions
that produced it so the decision is reproducible and auditable.
"""

from __future__ import annotations

CERTIFICATION_PROGRAM_VERSION: str = "certification-program@1.0.0"

CERTIFICATION_EVIDENCE_VERSION: str = "certification-evidence@1.0.0"
CERTIFICATION_AUDIT_VERSION: str = "certification-audit@1.0.0"
CERTIFICATION_READINESS_VERSION: str = "certification-readiness@1.0.0"
CERTIFICATION_COMPLIANCE_VERSION: str = "certification-compliance@1.0.0"
CERTIFICATION_DEPLOYMENT_VERSION: str = "certification-deployment@1.0.0"
CERTIFICATION_RISK_VERSION: str = "certification-risk@1.0.0"
CERTIFICATION_GAP_VERSION: str = "certification-gap@1.0.0"
CERTIFICATION_SCORECARD_VERSION: str = "certification-scorecard@1.0.0"
CERTIFICATION_DECISION_VERSION: str = "certification-decision@1.0.0"
CERTIFICATION_REPORT_VERSION: str = "certification-report@1.0.0"

# The three possible certification verdicts (closed vocabulary).
CERTIFIED = "CERTIFIED"
CONDITIONALLY_CERTIFIED = "CONDITIONALLY CERTIFIED"
NOT_CERTIFIED = "NOT CERTIFIED"

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
