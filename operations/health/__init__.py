"""``operations/health`` — health & readiness checks (P8-E).

Probes the **real** P1-P7 systems (it imports ``backend``/``frontend`` — operations is the
top-level ops layer, like ``scripts``) and reports structured health. It never modifies
any workflow; it constructs services and exercises read-only/structural paths:

* liveness   — the process is running.
* backend    — ``ApplicationBackendService`` constructs and its API answers a request.
* frontend   — the frontend renders its login page (presentation operational).
* model      — the model-foundation architectures are importable.
* storage    — the workspace is writable and a registry round-trips.
* workflow   — the workflow service is wired and the stage contract is intact.
* readiness  — config valid + storage + backend constructible (ready to serve).
* system     — aggregate of the component checks.

A heavy, opt-in ``smoke_pipeline`` runs a full upload->prediction through the real stack.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import Optional

from ..config import ConfigLoader, ConfigValidator
from ..version import OPERATIONS_HEALTH_VERSION

_EXPECTED_STAGES = ("upload", "validate", "process", "features", "predict", "confidence",
                    "explanation")


@dataclass(frozen=True)
class HealthStatus:
    component: str
    healthy: bool
    detail: str = ""

    def to_dict(self) -> dict:
        return {"component": self.component, "healthy": self.healthy, "detail": self.detail}


class _ProbeGateway:
    """A benign gateway for the frontend health probe (login rendering never calls it)."""

    api_version = "v1"

    def handle(self, operation: str, params=None, token=None) -> dict:
        return {"status": "not_found", "body": {}, "error_code": "probe", "ok": False,
                "api_version": "v1"}


class HealthChecker:
    """Runs the operational health checks against the real systems."""

    def __init__(self, *, workspace_dir: Optional[str] = None):
        self.workspace_dir = workspace_dir or tempfile.mkdtemp(prefix="nv_health_")

    # --- individual checks ----------------------------------------------------
    def liveness(self) -> HealthStatus:
        return HealthStatus("liveness", True, "process alive")

    def backend(self) -> HealthStatus:
        try:
            from backend.application_backend import (
                ApplicationBackendService, ApiRequest, ApiOperation, DeterministicEntropy,
            )
            svc = ApplicationBackendService(
                workspace_dir=os.path.join(self.workspace_dir, "be"),
                entropy=DeterministicEntropy("health"))
            resp = svc.api.handle(ApiRequest(ApiOperation.LOGIN,
                                             {"username": "x", "password": "y"}))
            ok = svc.api.version == "v1" and isinstance(resp.to_dict().get("status"), str)
            return HealthStatus("backend", ok, f"api={svc.api.version} login_probe={resp.status.value}")
        except Exception as exc:
            return HealthStatus("backend", False, f"error: {exc}")

    def frontend(self) -> HealthStatus:
        try:
            from frontend.application_frontend import FrontendApp
            app = FrontendApp(_ProbeGateway())
            html = app.render_login()
            ok = isinstance(html, str) and "<nav>" in html and "<script" not in html.lower()
            return HealthStatus("frontend", ok, f"login_page_bytes={len(html)}")
        except Exception as exc:
            return HealthStatus("frontend", False, f"error: {exc}")

    def model(self) -> HealthStatus:
        try:
            from backend.model_foundation import ModelArchitecture
            archs = {a.value for a in ModelArchitecture}
            ok = "eegnet" in archs
            return HealthStatus("model", ok, f"architectures={sorted(archs)}")
        except Exception as exc:
            return HealthStatus("model", False, f"error: {exc}")

    def storage(self) -> HealthStatus:
        try:
            root = os.path.join(self.workspace_dir, "storage_probe")
            os.makedirs(root, exist_ok=True)
            probe = os.path.join(root, "probe.txt")
            with open(probe, "w", encoding="utf-8") as fh:
                fh.write("ok")
            with open(probe, "r", encoding="utf-8") as fh:
                content = fh.read()
            os.remove(probe)
            from backend.application_backend import BackendRegistry
            reg_ok = isinstance(BackendRegistry().to_dict(), dict)
            return HealthStatus("storage", content == "ok" and reg_ok, "workspace writable; registry ok")
        except Exception as exc:
            return HealthStatus("storage", False, f"error: {exc}")

    def workflow(self) -> HealthStatus:
        try:
            from backend.application_backend import ApplicationBackendService, DeterministicEntropy
            from frontend.application_frontend import WORKFLOW_STAGES
            svc = ApplicationBackendService(
                workspace_dir=os.path.join(self.workspace_dir, "wf"),
                entropy=DeterministicEntropy("health"))
            wired = svc.workflow_service is not None and svc.inference_service is not None
            ok = wired and tuple(WORKFLOW_STAGES) == _EXPECTED_STAGES
            return HealthStatus("workflow", ok, f"wired={wired} stages={len(_EXPECTED_STAGES)}")
        except Exception as exc:
            return HealthStatus("workflow", False, f"error: {exc}")

    def readiness(self, *, environment: str = "testing") -> HealthStatus:
        try:
            config = ConfigLoader().load(environment)
            checks = ConfigValidator().validate(config)
            cfg_ok = all(c.passed for c in checks)
            storage_ok = self.storage().healthy
            backend_ok = self.backend().healthy
            ok = cfg_ok and storage_ok and backend_ok
            return HealthStatus("readiness", ok,
                                f"config_ok={cfg_ok} storage_ok={storage_ok} backend_ok={backend_ok}")
        except Exception as exc:
            return HealthStatus("readiness", False, f"error: {exc}")

    def system(self) -> HealthStatus:
        components = [self.backend(), self.frontend(), self.model(), self.storage(), self.workflow()]
        ok = all(c.healthy for c in components)
        return HealthStatus("system", ok,
                            "; ".join(f"{c.component}={'up' if c.healthy else 'down'}"
                                      for c in components))

    # --- full set -------------------------------------------------------------
    def check_all(self, *, environment: str = "testing") -> dict:
        statuses = [
            self.liveness(), self.backend(), self.frontend(), self.model(), self.storage(),
            self.workflow(), self.readiness(environment=environment),
        ]
        statuses.append(HealthStatus("system", all(
            s.healthy for s in statuses if s.component in
            ("backend", "frontend", "model", "storage", "workflow")), "aggregate"))
        return {
            "health_version": OPERATIONS_HEALTH_VERSION,
            "healthy": all(s.healthy for s in statuses),
            "components": {s.component: s.to_dict() for s in statuses},
        }

    # --- heavy, opt-in end-to-end smoke (real upload -> prediction) -----------
    def smoke_pipeline(self, cohort_files, sample_file: str) -> HealthStatus:
        """Drive a full register -> login -> upload -> analyse through the real backend
        API directly (operations may import backend). Proves the deployable pipeline."""
        try:
            from backend.application_backend import (
                ApplicationBackendService, ApiRequest, ApiOperation, DeterministicEntropy,
            )
            from backend.model_foundation import ModelArchitecture
            svc = ApplicationBackendService(
                workspace_dir=os.path.join(self.workspace_dir, "smoke"),
                entropy=DeterministicEntropy("health-smoke"))
            svc.prepare_model(cohort_files, architecture=ModelArchitecture.EEGNET,
                              dataset_key="cohort", seed=7)
            api = svc.api
            api.handle(ApiRequest(ApiOperation.REGISTER_USER,
                                  {"username": "ops.smoke", "password": "password123",
                                   "roles": ["clinician"]}))
            token = api.handle(ApiRequest(ApiOperation.LOGIN,
                                          {"username": "ops.smoke", "password": "password123"})
                               ).body["token"]
            with open(sample_file, "rb") as fh:
                content = fh.read()
            uid = api.handle(ApiRequest(ApiOperation.UPLOAD_EEG,
                                        {"filename": "rec.edf", "content": content},
                                        token=token)).body["upload_id"]
            res = api.handle(ApiRequest(ApiOperation.START_ANALYSIS, {"upload_id": uid}, token=token))
            ok = res.ok and bool(res.body.get("prediction_id"))
            return HealthStatus("smoke_pipeline", ok,
                                f"prediction={res.body.get('prediction_id')}")
        except Exception as exc:
            return HealthStatus("smoke_pipeline", False, f"error: {exc}")


def build_health_report(result: dict) -> dict:
    return {"report_type": "health", **result}


__all__ = ["HealthChecker", "HealthStatus", "build_health_report"]
