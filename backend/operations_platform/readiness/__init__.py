"""``backend/operations_platform/readiness`` — Deployment Readiness Engine (T4-F).

Combines the operational evidence (operational / monitoring / health / qualification /
registry / audit / lineage) into a deterministic score, findings, and a classification:

    NOT_READY  <  PARTIALLY_READY  <  READY_FOR_DEPLOYMENT

The system is ``READY_FOR_DEPLOYMENT`` only when health is HEALTHY, monitoring is active,
deployment qualification is QUALIFIED, diagnostics pass, and all of it is registered +
audited + traceable — i.e. complete, reproducible operational evidence.
"""

from __future__ import annotations

from ml.provenance import hash_obj

from ..models.domain import (
    DeploymentReadinessClass, DeploymentReadinessRecord, HealthState, QualificationStatus,
    ReadinessDimension,
)
from ..version import DETERMINISTIC_EPOCH

_WEIGHTS = {ReadinessDimension.OPERATIONAL.value: 0.2, ReadinessDimension.MONITORING.value: 0.15,
            ReadinessDimension.HEALTH.value: 0.2, ReadinessDimension.QUALIFICATION.value: 0.2,
            ReadinessDimension.REGISTRY.value: 0.1, ReadinessDimension.AUDIT.value: 0.05,
            ReadinessDimension.LINEAGE.value: 0.1}


class DeploymentReadinessEngine:
    def assess(self, *, health, metrics, diagnostic, qualification, registered: bool,
               audited: bool, traceable: bool,
               created_at: str = DETERMINISTIC_EPOCH) -> DeploymentReadinessRecord:
        health_ok = health.overall == HealthState.HEALTHY
        monitoring_ok = bool(metrics.deterministic_metrics)
        operational_ok = diagnostic.ok
        qualification_ok = qualification.status == QualificationStatus.QUALIFIED
        qualification_partial = qualification.status == QualificationStatus.CONDITIONALLY_QUALIFIED

        dims = {
            ReadinessDimension.OPERATIONAL.value: 1.0 if operational_ok else 0.0,
            ReadinessDimension.MONITORING.value: 1.0 if monitoring_ok else 0.0,
            ReadinessDimension.HEALTH.value: (1.0 if health_ok
                                              else (0.5 if health.overall == HealthState.DEGRADED
                                                    else 0.0)),
            ReadinessDimension.QUALIFICATION.value: (1.0 if qualification_ok
                                                     else (0.5 if qualification_partial else 0.0)),
            ReadinessDimension.REGISTRY.value: 1.0 if registered else 0.0,
            ReadinessDimension.AUDIT.value: 1.0 if audited else 0.0,
            ReadinessDimension.LINEAGE.value: 1.0 if traceable else 0.0,
        }
        score = round(sum(_WEIGHTS[d] * v for d, v in dims.items()), 6)
        findings = [d for d, v in sorted(dims.items()) if v < 1.0]

        all_ready = (health_ok and monitoring_ok and operational_ok and qualification_ok
                     and registered and audited and traceable)
        if all_ready and score >= 0.999:
            classification = DeploymentReadinessClass.READY_FOR_DEPLOYMENT
        elif score >= 0.5 and operational_ok:
            classification = DeploymentReadinessClass.PARTIALLY_READY
        else:
            classification = DeploymentReadinessClass.NOT_READY

        readiness_id = "ops_readiness+" + hash_obj({"dimensions": dims,
                                                    "classification": classification.value})
        return DeploymentReadinessRecord(
            readiness_id=readiness_id, score=score, classification=classification,
            dimensions=dims, findings=tuple(findings), created_at=created_at)


__all__ = ["DeploymentReadinessEngine"]
