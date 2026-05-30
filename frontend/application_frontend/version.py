"""Version identities for the Application Frontend Platform (Productization P7).

Every frontend view-model, page, state snapshot, validation result, and report records
the versions that produced it, so the presentation layer is reproducible and auditable
(mirrors the other subsystems). Bump a version when the named behaviour changes.

This module is **stdlib-only** (NR-8): the frontend imports no domain module.
"""

from __future__ import annotations

APPLICATION_FRONTEND_VERSION: str = "application-frontend@1.0.0"

FRONTEND_DOMAIN_VERSION: str = "frontend-domain@1.0.0"
FRONTEND_GATEWAY_VERSION: str = "frontend-gateway@1.0.0"
FRONTEND_STATE_VERSION: str = "frontend-state@1.0.0"
FRONTEND_VIEWMODEL_VERSION: str = "frontend-viewmodel@1.0.0"
FRONTEND_VALIDATION_VERSION: str = "frontend-validation@1.0.0"
FRONTEND_REPORT_VERSION: str = "frontend-report@1.0.0"

# The backend API version this frontend is built to consume.
CONSUMES_API_VERSION: str = "v1"

# Deterministic default timestamp (no wall-clock enters any rendered output).
DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
