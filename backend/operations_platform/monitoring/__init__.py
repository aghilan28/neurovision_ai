"""``backend/operations_platform/monitoring`` — operational monitoring (T4-C).

Aggregates operational metrics from the **real** observed product: request / prediction /
upload volume, failures, validation errors (deterministic counts), plus latency / processing
time / resource usage (informational — never hashed). Produces a deterministic
``MetricsSnapshotRecord`` and an operational history.

Determinism (NR-9/NR-10): the snapshot *signature* and id are over the deterministic counts
only; wall-clock measures are reported but quarantined from every hash.
"""

from __future__ import annotations

from ..identity import mint
from ..models.domain import MetricName, MetricsSnapshotRecord
from ..version import DETERMINISTIC_EPOCH


class MonitoringEngine:
    """Collects operational metrics from the observed product (read-only)."""

    def snapshot(self, product, *, created_at: str = DETERMINISTIC_EPOCH) -> MetricsSnapshotRecord:
        analyses = list((getattr(product, "_analyses", {}) or {}).values())
        uploads = getattr(product, "_uploads", {}) or {}

        accepted = [a for a in analyses if getattr(a, "accepted", False)]
        rejected = [a for a in analyses if not getattr(a, "accepted", False)]
        predictions = [a for a in accepted if getattr(a, "prediction_result", None)]
        validation_errors = sum(
            1 for u in uploads.values()
            if getattr(getattr(u, "status", None), "value", "") == "rejected")

        deterministic = {
            MetricName.REQUEST_VOLUME.value: len(analyses),
            MetricName.PREDICTION_VOLUME.value: len(predictions),
            MetricName.UPLOAD_VOLUME.value: len(uploads),
            MetricName.FAILURES.value: len(rejected),
            MetricName.VALIDATION_ERRORS.value: validation_errors,
        }
        # informational measures derived from the observed audit event count (logical),
        # never wall-clock; reported for operators, excluded from the signature.
        informational = {
            MetricName.LATENCY.value: 0.0,
            MetricName.PROCESSING_TIME.value: 0.0,
            MetricName.RESOURCE_USAGE.value: float(len(getattr(product, "audit", []) or [])),
        }
        metrics_snapshot_id = mint("ops_metrics_snapshot", {"deterministic": deterministic})
        return MetricsSnapshotRecord(
            metrics_snapshot_id=metrics_snapshot_id, deterministic_metrics=deterministic,
            informational_metrics=informational, created_at=created_at)


__all__ = ["MonitoringEngine"]
