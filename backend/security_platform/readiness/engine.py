"""Security readiness engine (DRP5-K).

Combines the measured evidence (authentication / authorization / policy / registry / audit /
lineage / validation) into a deterministic readiness score, a classification (NOT_READY /
PARTIALLY_READY / READY), findings, and a record.

Readiness criteria (the directive): security can only be ``READY`` when authentication,
authorization, access control, and a policy engine exist, validation passes, and the registry
+ audit + lineage + a readiness score exist.
"""

from __future__ import annotations

from ml.provenance import hash_obj           # allowed: backend -> ml

from ..models.domain import ReadinessClass, ReadinessDimension, SecurityReadinessRecord
from ..version import DETERMINISTIC_EPOCH

_WEIGHTS = {
    ReadinessDimension.AUTHENTICATION.value: 0.2,
    ReadinessDimension.AUTHORIZATION.value: 0.2,
    ReadinessDimension.POLICY.value: 0.15,
    ReadinessDimension.REGISTRY.value: 0.15,
    ReadinessDimension.AUDIT.value: 0.15,
    ReadinessDimension.LINEAGE.value: 0.1,
    ReadinessDimension.VALIDATION.value: 0.05,
}


class SecurityReadinessEngine:
    """Deterministic readiness assessment for an end-to-end secured access."""

    def assess(self, *, target_id: str, authentication_ok: bool, authorization_ok: bool,
               policy_ok: bool, registered: bool, audited: bool, traceable: bool,
               validation_ok: bool, created_at: str = DETERMINISTIC_EPOCH) -> SecurityReadinessRecord:
        dimensions = {
            ReadinessDimension.AUTHENTICATION.value: 1.0 if authentication_ok else 0.0,
            ReadinessDimension.AUTHORIZATION.value: 1.0 if authorization_ok else 0.0,
            ReadinessDimension.POLICY.value: 1.0 if policy_ok else 0.0,
            ReadinessDimension.REGISTRY.value: 1.0 if registered else 0.0,
            ReadinessDimension.AUDIT.value: 1.0 if audited else 0.0,
            ReadinessDimension.LINEAGE.value: 1.0 if traceable else 0.0,
            ReadinessDimension.VALIDATION.value: 1.0 if validation_ok else 0.0,
        }
        score = round(sum(_WEIGHTS[d] * v for d, v in dimensions.items()), 6)
        findings = [d for d, v in sorted(dimensions.items()) if v < 1.0]

        all_present = (authentication_ok and authorization_ok and policy_ok and registered
                       and audited and traceable)
        if all_present and validation_ok and score >= 0.999:
            classification = ReadinessClass.READY
        elif score >= 0.5 and validation_ok:
            classification = ReadinessClass.PARTIALLY_READY
        else:
            classification = ReadinessClass.NOT_READY

        readiness_id = "security_readiness+" + hash_obj({
            "target_id": target_id, "dimensions": dimensions, "classification": classification.value})
        return SecurityReadinessRecord(
            readiness_id=readiness_id, target_id=target_id, score=score,
            classification=classification, dimensions=dimensions, findings=tuple(findings),
            created_at=created_at)


__all__ = ["SecurityReadinessEngine"]
