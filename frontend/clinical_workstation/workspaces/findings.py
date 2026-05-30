"""Findings workspace — render registered finding artifacts as Page view-models."""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges, validation_badges
from ..visualizations import finding_lifecycle


def finding_pages(state) -> list:
    pages = [_overview(state)]
    for finding in state.findings:
        pages.append(_finding_detail(finding))
    return pages


def _overview(state) -> Page:
    rows = []
    for f in state.findings:
        rec = f.get("registry_record", {})
        rows.append([f.get("finding_id", "")[:18], f.get("case_id", "")[:14],
                     rec.get("status"), rec.get("category") or rec.get("observation"),
                     len(f.get("interpretations", [])), f.get("validation", {}).get("ok")])
    sections = [
        kv_panel("Finding Registry", {
            "n_findings": len(state.findings),
            "registry_version": state.registries.get("finding_registry", {}).get("finding_registry_version"),
        }),
        table("Findings", ["finding", "case", "status", "category", "interps", "valid"], rows),
    ]
    return Page("findings-overview", "Findings — Overview", sections, [finding_lifecycle(state.findings)])


def _finding_detail(finding: dict) -> Page:
    rec = finding.get("registry_record", {})
    reports = finding.get("reports", {})
    evidence_report = reports.get("evidence_report", {})
    audit = finding.get("audit", {})
    fid = finding.get("finding_id", "")
    evidence_rows = []
    for ev in evidence_report.get("evidence", evidence_report.get("items", [])):
        evidence_rows.append([ev.get("evidence_type") or ev.get("type"),
                              ev.get("evidence_id", "")[:18] if ev.get("evidence_id") else "",
                              ev.get("evidence_confidence", ev.get("confidence"))])
    interp_rows = [[i.get("interpretation_id", "")[:18], i.get("confidence_level"),
                    (i.get("text") or "")[:48]] for i in finding.get("interpretations", [])]
    sections = [
        kv_panel("Finding Metadata", {
            "finding_id": fid, "case_id": finding.get("case_id"),
            "review_id": finding.get("review_id"), "category": rec.get("category"),
            "observation": rec.get("observation"), "version": rec.get("version"),
        }),
        badges("Lifecycle State", [
            ("status", rec.get("status", "?")),
            ("audit_verified", audit.get("verified", False)),
            ("lineage_verified", finding.get("lineage_verified", False)),
        ]),
        table("Finding Evidence", ["type", "evidence_id", "confidence"], evidence_rows),
        table("Interpretations", ["interpretation", "confidence_level", "text"], interp_rows),
        validation_badges("Finding Validation", finding.get("validation", {})),
        table("Version History (audit)", ["seq", "event", "hash"],
              [[e.get("seq"), e.get("kind"), e.get("event_hash", "")[:8]]
               for e in audit.get("events", [])]),
        kv_panel("Lineage", {"lineage_id": finding.get("lineage_id")}),
    ]
    return Page(f"finding-{fid}", f"Finding {fid[:14]}", sections, [])
