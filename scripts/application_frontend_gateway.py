"""The frontend↔backend seam (Productization P7).

This is the **only** place that imports both the backend and the frontend. It adapts the
real ``backend.application_backend.ApplicationAPI`` to the frontend's abstract
:class:`BackendGateway` port, so the presentation layer can drive the *actual* backend
contracts without importing any domain module (NR-8). Scripts may import any layer; this
is the sanctioned composition point (like ``run_offline_inference`` /
``build_workstation_snapshot``).

    from scripts.application_frontend_gateway import LiveBackendGateway, build_live_app
"""

from __future__ import annotations

import tempfile
from typing import Optional, Sequence

from backend.application_backend import ApplicationBackendService, ApiRequest, ApiOperation
from backend.model_foundation import ModelArchitecture
from frontend.application_frontend import BackendGateway, FrontendApp


class LiveBackendGateway(BackendGateway):
    """A concrete gateway that dispatches to a live ``ApplicationAPI`` instance."""

    def __init__(self, api):
        self.api = api
        self.call_log: list[str] = []

    def handle(self, operation: str, params: Optional[dict] = None,
               token: Optional[str] = None) -> dict:
        self.call_log.append(operation)
        response = self.api.handle(ApiRequest(ApiOperation(operation), params or {}, token=token))
        return response.to_dict()


def build_live_app(cohort_files: Sequence[tuple], *, workspace_dir: Optional[str] = None,
                   architecture: ModelArchitecture = ModelArchitecture.EEGNET,
                   dataset_key: str = "cohort", seed: int = 7, entropy=None):
    """Compose the real backend (with a prepared model) + a live gateway + a FrontendApp.

    Returns ``(service, gateway, app)``. The model is prepared via the backend's own
    ``prepare_model`` (a backend-admin step, not a UI action) so the frontend can then
    drive the user-facing flow end to end.
    """
    workspace_dir = workspace_dir or tempfile.mkdtemp(prefix="nv_p7_")
    service = ApplicationBackendService(workspace_dir=workspace_dir, entropy=entropy)
    service.prepare_model(cohort_files, architecture=architecture, dataset_key=dataset_key,
                          seed=seed)
    gateway = LiveBackendGateway(service.api)
    app = FrontendApp(gateway)
    return service, gateway, app


__all__ = ["LiveBackendGateway", "build_live_app"]
