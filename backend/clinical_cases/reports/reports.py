"""Case report builders (reproducible; version-tagged)."""

from __future__ import annotations

from typing import Any

from ..version import CASE_REPORT_VERSION, CLINICAL_CASES_VERSION
from ..lifecycle import CASE_TRANSITIONS, CaseLifecycle


def _header(report_type: str, case: Any) -> dict:
    return {
        "report_type": report_type,
        "case_report_version": CASE_REPORT_VERSION,
        "clinical_cases_version": CLINICAL_CASES_VERSION,
        "case_id": case.case_id,
        "patient_id": case.patient_id,
        "case_version": case.version.version,
    }


def build_case_summary_report(case: Any) -> dict:
    return {
        **_header("case_summary", case),
        "status": case.state.status.value,
        "owner": case.owner,
        "created_at": case.created_at,
        "n_studies": len(case.studies),
        "studies": [s.to_dict() for s in case.studies],
        "metadata": case.metadata.to_dict(),
        "lineage_id": case.lineage_id,
        "audit_head": case.audit_head,
    }


def build_case_audit_report(case: Any, audit_log: Any) -> dict:
    return {
        **_header("case_audit", case),
        "audit_head": audit_log.head,
        "chain_verified": audit_log.verify(),
        "n_events": len(audit_log),
        "events": [e.to_dict() for e in audit_log.events()],
    }


def build_case_lineage_report(case: Any, lineage_tracker: Any) -> dict:
    chain = lineage_tracker.chain(case.lineage_id) if case.lineage_id else []
    return {
        **_header("case_lineage", case),
        "lineage_id": case.lineage_id,
        "chain_verified": lineage_tracker.verify_chain(case.lineage_id) if case.lineage_id else False,
        "chain_length": len(chain),
        "chain": [r.to_dict() for r in chain],
    }


def build_case_lifecycle_report(case: Any, audit_log: Any) -> dict:
    transitions = [e.to_dict() for e in audit_log.events() if e.kind == "state_change"]
    return {
        **_header("case_lifecycle", case),
        "current_status": case.state.status.value,
        "transition_count": case.state.transition_count,
        "is_terminal": CaseLifecycle.is_terminal(case.state.status),
        "allowed_next": sorted(t.value for t in CaseLifecycle.allowed_targets(case.state.status)),
        "transitions": transitions,
        "state_machine": {s.value: sorted(t.value for t in targets)
                          for s, targets in CASE_TRANSITIONS.items()},
    }


def build_case_validation_report(case: Any, validation_report_dict: dict) -> dict:
    return {
        **_header("case_validation", case),
        "validation": validation_report_dict,
    }
