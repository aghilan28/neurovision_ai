"""``frontend/application_frontend/validation`` — frontend flow/state/UI validation (P7-J).

Structured, deterministic checks over the presentation layer: authentication, upload,
workflow, prediction, and report flows, plus state integrity, session integrity, and UI
integrity (every page renders and exposes navigation). These are presentation checks —
they never re-run business logic; they assert the UI faithfully reflects backend results
and holds no secrets.
"""

from __future__ import annotations

from typing import Optional

from ..version import FRONTEND_VALIDATION_VERSION
from ..workflows import WORKFLOW_STAGES


class FrontendValidationReport:
    """A tiny stdlib validation report (the frontend cannot import ml.validation)."""

    def __init__(self) -> None:
        self._checks: list[tuple[str, bool, str]] = []

    def add(self, name: str, passed: bool, detail: str = "") -> None:
        self._checks.append((name, bool(passed), detail))

    @property
    def ok(self) -> bool:
        return all(p for _, p, _ in self._checks)

    @property
    def checks(self):
        return tuple(self._checks)

    @property
    def n_checks(self) -> int:
        return len(self._checks)

    def failures(self):
        return [(n, d) for n, p, d in self._checks if not p]

    def to_dict(self) -> dict:
        return {
            "validation_version": FRONTEND_VALIDATION_VERSION, "ok": self.ok,
            "n_checks": self.n_checks,
            "checks": [{"name": n, "passed": p, "detail": d} for n, p, d in self._checks],
        }


class FrontendValidator:
    """Runs the eight frontend-integrity checks over a FrontendApp + its state."""

    def validate(self, app, *, analysis_id: Optional[str] = None) -> FrontendValidationReport:
        report = FrontendValidationReport()
        state = app.state
        snap = state.snapshot()

        # 1. authentication flow integrity
        if state.is_authenticated:
            ok = (snap["user"] is not None and snap["session"] is not None
                  and snap["session"]["user_id"] == snap["user"]["user_id"])
            report.add("authentication_flow_integrity", ok,
                       f"user={snap['user']['user_id'] if snap['user'] else None}")
        else:
            report.add("authentication_flow_integrity", snap["user"] is None,
                       "unauthenticated state is clean")

        # 2. upload flow integrity
        uploads = snap["uploads"]
        report.add("upload_flow_integrity",
                   all(u["upload_id"] and u["content_fingerprint"] for u in uploads),
                   f"n_uploads={len(uploads)}")

        # 3. workflow flow integrity (the analysis summary reports the analysis status,
        # "generated"; the full ordered stage set is enriched from the workflow report)
        wfs = snap["workflows"]
        wf_ok = all(w["status"] in ("completed", "generated")
                    and (not w["stages"] or tuple(w["stages"]) == WORKFLOW_STAGES)
                    for w in wfs) if wfs else True
        report.add("workflow_flow_integrity", wf_ok, f"n_workflows={len(wfs)}")

        # 4. prediction flow integrity
        preds = snap["predictions"]
        if preds:
            pred_ok = True
            for p in preds.values():
                probs = [c.get("probability", 0) for c in p["prediction"].get("classes", [])]
                total = sum(probs) if probs else 1.0
                pred_ok = pred_ok and bool(p["predicted_label"]) and bool(p["confidence_level"]) \
                    and abs(total - 1.0) < 1e-6
            report.add("prediction_flow_integrity", pred_ok, f"n_predictions={len(preds)}")
        else:
            report.add("prediction_flow_integrity", True, "no predictions in scope")

        # 5. report flow integrity
        reports = snap["reports"]
        if reports:
            rep_ok = all(any(r["name"] == "prediction_report" for r in rs)
                         for rs in reports.values())
            report.add("report_flow_integrity", rep_ok, f"n_report_sets={len(reports)}")
        else:
            report.add("report_flow_integrity", True, "no reports in scope")

        # 6. state integrity (deterministic + secret-free)
        deterministic = state.snapshot() == snap
        secret_free = "token" not in str(snap).lower().replace("token_fingerprint", "")
        report.add("state_integrity", deterministic and secret_free,
                   f"deterministic={deterministic} secret_free={secret_free}")

        # 7. session integrity
        if state.is_authenticated:
            sess_ok = state.token is not None and not snap["session_expired"]
        else:
            sess_ok = state.token is None
        report.add("session_integrity", sess_ok, f"authenticated={state.is_authenticated}")

        # 8. UI integrity (every page renders + carries nav)
        try:
            htmls = [app.render_login(), app.render_register()]
            if state.is_authenticated:
                htmls += [app.render_dashboard(), app.render_upload(), app.render_analysis()]
                if analysis_id:
                    htmls += [app.render_prediction(analysis_id), app.render_reports(analysis_id)]
            ui_ok = all(isinstance(h, str) and "<nav>" in h and len(h) > 200 for h in htmls)
            report.add("ui_integrity", ui_ok, f"pages_rendered={len(htmls)}")
        except Exception as exc:  # pragma: no cover - defensive
            report.add("ui_integrity", False, f"error: {exc}")

        return report


__all__ = ["FrontendValidator", "FrontendValidationReport"]
