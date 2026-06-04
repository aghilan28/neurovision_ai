"""Version identities for the Application Platform subsystem (Track 3).

Track 3 turns the model platform (Tracks 1 + 2 + P1-P10 + DRP-1..6) into a **usable
product**: a real FastAPI HTTP API + governed user workflows (EEG upload -> validate ->
features -> model select -> inference -> prediction -> report) over **real** EEG files and
**real** trained models.

It REUSES the existing ``application_backend`` hub (which already orchestrates the reused
P1-P5 upload -> analysis -> prediction workflow), the Track-1 ``dataset_acquisition`` real
recordings, the Track-2 ``real_model_training`` candidates, the shared ``ml.lineage``
tracker, the shared ``ImmutableAuditLog``, ``ml.validation`` and ``ml.provenance``. It adds
an HTTP API, a product workflow/registry/readiness/report layer — it retrains no models and
modifies no datasets, Track 1, Track 2, persistence, security, or deployment.
"""

from __future__ import annotations

APPLICATION_PLATFORM_VERSION: str = "application-platform@1.0.0"
API_V1: str = "v1"

APP_DOMAIN_VERSION: str = "app-domain@1.0.0"
APP_IDENTITY_VERSION: str = "app-identity@1.0.0"
APP_API_VERSION: str = "app-api@1.0.0"
APP_WORKFLOW_VERSION: str = "app-workflow@1.0.0"
APP_UPLOAD_VERSION: str = "app-upload@1.0.0"
APP_PREDICTION_VERSION: str = "app-prediction@1.0.0"
APP_REPORT_VERSION: str = "app-report@1.0.0"
APP_VALIDATION_VERSION: str = "app-validation@1.0.0"
APP_READINESS_VERSION: str = "app-readiness@1.0.0"
APP_REGISTRY_VERSION: str = "app-registry@1.0.0"
APP_AUDIT_VERSION: str = "app-audit@1.0.0"
APP_LINEAGE_VERSION: str = "app-lineage@1.0.0"
# MP-3 — persistent model lifecycle & recovery (durable model identity + verified recovery).
APP_MODEL_LIFECYCLE_VERSION: str = "app-model-lifecycle@1.0.0"

# Bounded analysis window (seconds). Real EEG recordings can be hours long; the product
# analyses a deterministic bounded leading segment so a user workflow returns promptly. The
# full recording is stored intact; only the analysis is bounded (a clinical-epoch approach).
DEFAULT_ANALYSIS_SECONDS: float = 5.0

DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
FINGERPRINT_DECIMALS: int = 9
