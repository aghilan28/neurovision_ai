"""``backend/operations_platform/diagnostics`` — diagnostic engine (T4-D).

Diagnoses the observed product across workflow / prediction / upload / API / failure domains
and classifies a root cause (closed vocabulary). Produces structured diagnostic findings
(never exceptions) and a deterministic ``DiagnosticRecord``. Read-only — it inspects state
that the product already produced; it never re-runs business logic.
"""

from __future__ import annotations

from ..identity import mint
from ..models.domain import (
    DiagnosticDomain, DiagnosticFinding, DiagnosticRecord, RootCause, Severity,
)
from ..version import DETERMINISTIC_EPOCH

_INFO, _WARN, _ERR = Severity.INFO, Severity.WARNING, Severity.ERROR


class DiagnosticEngine:
    """Runs operational diagnostics over the observed product (read-only)."""

    def diagnose(self, product, *, created_at: str = DETERMINISTIC_EPOCH) -> DiagnosticRecord:
        findings: list[DiagnosticFinding] = []

        def add(domain, passed, severity, root_cause, detail=""):
            findings.append(DiagnosticFinding(domain=domain, severity=severity,
                                              passed=bool(passed), root_cause=root_cause,
                                              detail=detail))

        info = getattr(product, "_model_info", {}) or {}
        analyses = list((getattr(product, "_analyses", {}) or {}).values())
        accepted = [a for a in analyses if getattr(a, "accepted", False)]
        rejected = [a for a in analyses if not getattr(a, "accepted", False)]

        # --- API: dispatcher present + reachable ---
        api_ok = hasattr(getattr(product.backend, "api", None), "handle")
        add(DiagnosticDomain.API, api_ok, _ERR if not api_ok else _INFO,
            RootCause.API_ERROR if not api_ok else RootCause.NONE,
            "API dispatcher reachable" if api_ok else "API dispatcher missing")

        # --- upload: rejected uploads classified as invalid input (not a defect) ---
        if rejected:
            add(DiagnosticDomain.UPLOAD, True, _WARN, RootCause.INVALID_UPLOAD,
                f"{len(rejected)} upload(s) rejected by validation (handled gracefully)")
        else:
            add(DiagnosticDomain.UPLOAD, True, _INFO, RootCause.NONE, "no rejected uploads")

        # --- prediction: a model is available + produced labelled predictions ---
        if not info.get("model_id"):
            add(DiagnosticDomain.PREDICTION, False, _ERR, RootCause.MISSING_MODEL,
                "no model prepared")
        else:
            preds = [a for a in accepted if getattr(a, "prediction_result", None)
                     and a.prediction_result.predicted_label != ""]
            ok = bool(preds) or not accepted  # ok if predictions exist, or nothing to predict yet
            add(DiagnosticDomain.PREDICTION, ok, _INFO if ok else _ERR,
                RootCause.NONE if ok else RootCause.WORKFLOW_INCOMPLETE,
                f"labelled_predictions={len(preds)}")

        # --- workflow: accepted analyses completed + traceable ---
        incomplete = [a for a in accepted
                      if not (getattr(a, "workflow", None) and a.workflow.status.value == "completed")]
        if incomplete:
            add(DiagnosticDomain.WORKFLOW, False, _ERR, RootCause.WORKFLOW_INCOMPLETE,
                f"{len(incomplete)} accepted analysis(es) not completed")
        else:
            add(DiagnosticDomain.WORKFLOW, True, _INFO, RootCause.NONE,
                f"completed_workflows={len(accepted)}")

        # --- failure: audit chain intact (corrupted-state detector) ---
        try:
            audit_ok = product.audit.verify()
        except Exception:  # noqa: BLE001
            audit_ok = False
        add(DiagnosticDomain.FAILURE, audit_ok, _ERR if not audit_ok else _INFO,
            RootCause.CORRUPTED_STATE if not audit_ok else RootCause.NONE,
            "audit chain intact" if audit_ok else "audit chain verification failed")

        ok = all(f.passed or not f.severity.blocking for f in findings)
        root_causes = sorted({f.root_cause.value for f in findings
                              if f.root_cause != RootCause.NONE})
        diagnostic_id = mint("ops_diagnostic", {
            "findings": [[f.domain.value, f.severity.value, f.passed, f.root_cause.value]
                         for f in findings]})
        return DiagnosticRecord(diagnostic_id=diagnostic_id, ok=ok, findings=tuple(findings),
                                root_causes=tuple(root_causes), created_at=created_at)


__all__ = ["DiagnosticEngine"]
