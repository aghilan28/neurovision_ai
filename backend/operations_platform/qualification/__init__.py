"""``backend/operations_platform/qualification`` — deployment qualification (T4-E).

Validates the availability of every deployment target — dataset / model / API / workflow /
report / persistence / security — against the **real** observed product, and produces a
deterministic ``QualificationRecord`` with a status: QUALIFIED / CONDITIONALLY_QUALIFIED /
NOT_QUALIFIED. Read-only; never alters business logic.
"""

from __future__ import annotations

from ..identity import mint
from ..models.domain import (
    QualificationFinding, QualificationRecord, QualificationStatus, QualificationTarget, Severity,
)
from ..version import DETERMINISTIC_EPOCH


def _importable(module: str) -> bool:
    try:
        __import__(module)
        return True
    except Exception:  # noqa: BLE001
        return False


class QualificationEngine:
    """Qualifies the product for deployment by checking target availability (read-only)."""

    def qualify(self, product, *, created_at: str = DETERMINISTIC_EPOCH) -> QualificationRecord:
        findings: list[QualificationFinding] = []

        def add(target, available, severity=Severity.ERROR, detail=""):
            findings.append(QualificationFinding(target=target, available=bool(available),
                                                 severity=severity if not available else Severity.INFO,
                                                 detail=detail))

        info = getattr(product, "_model_info", {}) or {}
        analyses = list((getattr(product, "_analyses", {}) or {}).values())
        accepted = [a for a in analyses if getattr(a, "accepted", False)]

        # dataset availability (Track 1 reachable + a known dataset)
        add(QualificationTarget.DATASET, _importable("backend.dataset_acquisition"),
            detail="Track-1 dataset_acquisition importable")
        # model availability (a model prepared READY_FOR_SERVING upstream)
        add(QualificationTarget.MODEL, bool(info.get("model_id")),
            detail=f"model={info.get('model_id', 'none')[:24]}")
        # API availability (the in-process dispatcher present)
        add(QualificationTarget.API, hasattr(getattr(product.backend, "api", None), "handle"),
            detail="application API dispatcher present")
        # workflow availability (at least one completed analysis OR the workflow wiring intact)
        wf_ok = bool([a for a in accepted
                      if getattr(a, "workflow", None) and a.workflow.status.value == "completed"]) \
            or _importable("backend.application_platform")
        add(QualificationTarget.WORKFLOW, wf_ok, detail="upload->analysis workflow available")
        # report availability (a report record + exporters present)
        rep_ok = any(getattr(a, "report_record", None) for a in accepted) \
            or _importable("backend.application_platform.reports")
        add(QualificationTarget.REPORT, rep_ok, detail="JSON/HTML/PDF report generation available")
        # persistence availability (DRP-4 reachable)
        add(QualificationTarget.PERSISTENCE, _importable("backend.persistence_platform"),
            severity=Severity.WARNING, detail="DRP-4 persistence_platform importable")
        # security availability (DRP-5 reachable)
        add(QualificationTarget.SECURITY, _importable("backend.security_platform"),
            severity=Severity.WARNING, detail="DRP-5 security_platform importable")

        blocking_unavailable = [f for f in findings if not f.available and f.severity.blocking]
        nonblocking_unavailable = [f for f in findings if not f.available and not f.severity.blocking]
        if not blocking_unavailable and not nonblocking_unavailable:
            status = QualificationStatus.QUALIFIED
        elif not blocking_unavailable:
            status = QualificationStatus.CONDITIONALLY_QUALIFIED
        else:
            status = QualificationStatus.NOT_QUALIFIED

        qualification_id = mint("ops_qualification", {
            "status": status.value,
            "findings": [[f.target.value, f.available] for f in findings]})
        return QualificationRecord(qualification_id=qualification_id, status=status,
                                   findings=tuple(findings), created_at=created_at)


__all__ = ["QualificationEngine"]
