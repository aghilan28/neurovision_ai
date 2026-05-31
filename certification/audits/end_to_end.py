"""End-to-end certification (P10-D).

Runs the complete user journey through the **real** systems and certifies each step with
objective evidence: user login, EEG upload, processing, feature generation, prediction,
confidence, explanation, report generation, operational monitoring, and recovery. Reuses
the P6 application backend API + the P8 operations layer; it builds nothing new.
"""

from __future__ import annotations

import os
import tempfile

from ..util import fingerprint
from ..version import CERTIFICATION_AUDIT_VERSION

_COHORT = ["valid.edf", "valid_edf_plus.edf", "valid.bdf", "valid_bdf_plus.bdf",
           "valid_raw.fif", "valid.set"]


class EndToEndCertification:
    """Certifies the full deployable journey end to end."""

    def run(self, fixtures: dict, *, workspace_dir: str = None) -> dict:
        from backend.application_backend import (
            ApplicationBackendService, ApiRequest, ApiOperation, DeterministicEntropy,
        )
        from backend.model_foundation import ModelArchitecture
        from operations.monitoring import MetricsRegistry, build_monitoring_report
        from operations.backups import BackupManager
        from operations.recovery import RestoreManager
        from operations.config import ConfigLoader

        ws = workspace_dir or tempfile.mkdtemp(prefix="nv_p10_e2e_")
        svc = ApplicationBackendService(workspace_dir=ws, entropy=DeterministicEntropy("p10-e2e"))
        cohort = [(f"P-{i}", f"C-{i}", fixtures[n]) for i, n in enumerate(_COHORT)]
        svc.prepare_model(cohort, architecture=ModelArchitecture.EEGNET, dataset_key="cohort", seed=7)
        api = svc.api
        metrics = MetricsRegistry()
        checks = []

        def record(name, ok, evidence=""):
            checks.append({"name": name, "passed": bool(ok), "evidence": str(evidence)[:160]})

        def call(op, params, token=None):
            resp = api.handle(ApiRequest(op, params, token=token))
            metrics.record_request(op.value, resp.status.value)
            return resp

        # 1. registration + login
        reg = call(ApiOperation.REGISTER_USER,
                   {"username": "cert.user", "password": "password123", "roles": ["clinician"]})
        login = call(ApiOperation.LOGIN, {"username": "cert.user", "password": "password123"})
        token = login.body.get("token")
        record("user_login", reg.ok and login.ok and bool(token),
                f"register={reg.status.value} login={login.status.value}")

        # 2. EEG upload
        with open(fixtures["valid.edf"], "rb") as fh:
            content = fh.read()
        up = call(ApiOperation.UPLOAD_EEG, {"filename": "rec.edf", "content": content}, token=token)
        upload_id = up.body.get("upload_id")
        record("eeg_upload", up.ok and bool(upload_id), f"upload={up.status.value}")

        # 3. analysis (processing/features/prediction) via the workflow
        an = call(ApiOperation.START_ANALYSIS, {"upload_id": upload_id}, token=token)
        analysis_id = an.body.get("analysis_id")
        ok_analysis = an.ok and bool(analysis_id)
        # confirm processing + feature stages from the workflow report
        reports = call(ApiOperation.LIST_REPORTS, {"analysis_id": analysis_id}, token=token) if ok_analysis else None
        stages = []
        if reports and reports.ok:
            wf = reports.body.get("reports", {}).get("workflow_report", {})
            stages = wf.get("stages", [])
        # retrieve prediction / confidence / explanation (exercises the real P5 assets)
        pred = call(ApiOperation.RETRIEVE_PREDICTION, {"analysis_id": analysis_id}, token=token) if ok_analysis else None
        conf = call(ApiOperation.RETRIEVE_CONFIDENCE, {"analysis_id": analysis_id}, token=token) if ok_analysis else None
        expl = call(ApiOperation.RETRIEVE_EXPLANATION, {"analysis_id": analysis_id}, token=token) if ok_analysis else None

        record("eeg_processing", ok_analysis and "process" in stages, f"stages={stages}")
        record("feature_generation", ok_analysis and "features" in stages, f"stages={stages}")
        record("prediction_generation",
                ok_analysis and "predict" in stages and bool(pred and pred.ok)
                and bool((pred.body.get("prediction") or {}) if pred else False),
                f"predicted_class={an.body.get('predicted_class')}")

        record("confidence_generation", bool(conf and conf.ok)
                and bool((conf.body.get("confidence") or {}).get("confidence_level") if conf else False),
                f"level={(conf.body.get('confidence') or {}).get('confidence_level') if conf else None}")
        record("explanation_generation", bool(expl and expl.ok)
                and bool((expl.body.get("explanation") or {}).get("method") if expl else False),
                f"method={(expl.body.get('explanation') or {}).get('method') if expl else None}")

        # 7. report generation
        report_names = reports.body.get("report_names", []) if (reports and reports.ok) else []
        record("report_generation", bool(report_names) and "prediction_report" in report_names,
                f"reports={len(report_names)}")

        # 8. operational monitoring (metrics emitted from the journey, no cloud)
        mon = build_monitoring_report(metrics)
        record("operational_monitoring", mon["cloud_dependencies"] is False
                and mon["n_counters"] >= 1, f"counters={mon['n_counters']}")

        # 9. recovery capability (backup + verified restore of the live registry)
        dest = os.path.join(ws, "backup")
        manifest = BackupManager().backup(dest, registry=svc.registry,
                                         config=ConfigLoader().load("testing"))
        restore = RestoreManager().restore(dest)
        record("recovery_capability", bool(manifest.signature) and restore.ok,
                f"backup={manifest.backup_id} restore_ok={restore.ok}")

        ok = all(c["passed"] for c in checks)
        return {
            "audit_version": CERTIFICATION_AUDIT_VERSION, "ok": ok,
            "n_checks": len(checks), "checks": checks,
            "prediction_id": an.body.get("prediction_id") if ok_analysis else None,
            "monitoring": mon,
            "signature": fingerprint({"checks": [(c["name"], c["passed"]) for c in checks]}),
        }


__all__ = ["EndToEndCertification"]
