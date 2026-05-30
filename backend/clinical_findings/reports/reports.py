"""Finding report builders (reproducible; version-tagged)."""

from __future__ import annotations

from typing import Any, Mapping

from ..version import FINDING_REPORT_VERSION, CLINICAL_FINDINGS_VERSION
from ..lifecycle import FINDING_TRANSITIONS, FindingLifecycle


def _header(report_type: str, finding: Any) -> dict:
    return {
        "report_type": report_type,
        "finding_report_version": FINDING_REPORT_VERSION,
        "clinical_findings_version": CLINICAL_FINDINGS_VERSION,
        "finding_id": finding.finding_id,
        "case_id": finding.case_id,
        "review_id": finding.review_id,
        "finding_version": finding.version.version,
    }


def build_finding_summary_report(finding: Any) -> dict:
    return {
        **_header("finding_summary", finding),
        "status": finding.status.value,
        "study_id": finding.study_id,
        "observation": finding.record.observation,
        "category": finding.record.category,
        "owner": finding.owner,
        "n_evidence": len(finding.evidence),
        "n_interpretations": len(finding.interpretation_ids),
        "lineage_id": finding.lineage_id,
        "audit_head": finding.audit_head,
        "allowed_next": sorted(t.value for t in FindingLifecycle.allowed_targets(finding.status)),
    }


def build_finding_audit_report(finding: Any, audit_log: Any) -> dict:
    return {
        **_header("finding_audit", finding),
        "audit_head": audit_log.head,
        "chain_verified": audit_log.verify(),
        "n_events": len(audit_log),
        "events": [e.to_dict() for e in audit_log.events()],
    }


def build_finding_lineage_report(finding: Any, lineage_tracker: Any) -> dict:
    chain = lineage_tracker.chain(finding.lineage_id) if finding.lineage_id else []
    return {
        **_header("finding_lineage", finding),
        "lineage_id": finding.lineage_id,
        "review_lineage_id": finding.review_lineage_id,
        "inference_lineage_id": finding.inference_lineage_id,
        "chain_verified": lineage_tracker.verify_chain(finding.lineage_id) if finding.lineage_id else False,
        "chain_length": len(chain),
        "chain_kinds": sorted({r.kind for r in chain}),
        "chain": [r.to_dict() for r in chain],
    }


def build_finding_validation_report(finding: Any, validation_report_dict: dict) -> dict:
    return {**_header("finding_validation", finding), "validation": validation_report_dict}


def build_evidence_report(finding: Any) -> dict:
    return {
        **_header("finding_evidence", finding),
        "n_evidence": len(finding.evidence),
        "evidence": [e.to_dict() for e in finding.evidence],
    }


def build_interpretation_report(finding: Any, interpretations: Mapping[str, Any]) -> dict:
    items = [interpretations[i].to_dict() for i in finding.interpretation_ids if i in interpretations]
    return {
        **_header("finding_interpretation", finding),
        "n_interpretations": len(items),
        "interpretations": items,
    }
