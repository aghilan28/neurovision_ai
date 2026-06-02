"""Intelligence workspace — render registered V2-P5 intelligence artifacts."""

from __future__ import annotations

from ..schemas import Page
from ..components import kv_panel, table, badges, validation_badges
from ..visualizations import population_analytics, trend_analysis, quality_metrics


def intelligence_pages(state) -> list:
    intel = state.intelligence
    if not intel:
        return [Page("intelligence", "Intelligence", [kv_panel("Intelligence", {"available": False})], [])]
    analytics = intel.get("analytics", {}).get("artifact", {})
    trend = intel.get("trend", {}).get("artifact", {})
    quality = intel.get("quality", {}).get("artifact", {})
    cohort = intel.get("cohort", {}).get("artifact", {})
    audit = intel.get("audit", {})

    blocks_rows = []
    for b in analytics.get("blocks", []):
        blocks_rows.append([b.get("subject_kind"), b.get("count"),
                            ", ".join(sorted((b.get("distributions") or {}).keys()))])

    trend_rows = [[s.get("metric"), s.get("direction"), s.get("delta"), len(s.get("points", []))]
                  for s in trend.get("series", [])]
    quality_rows = [[m.get("name"), m.get("value"), m.get("numerator"), m.get("denominator")]
                    for m in quality.get("metrics", [])]

    sections = [
        kv_panel("Intelligence Registry", {
            "n_artifacts": intel.get("registry", {}).get("n_artifacts"),
            "registry_version": intel.get("registry", {}).get("intel_registry_version"),
        }),
        kv_panel("Cohort", {
            "cohort_id": cohort.get("cohort_id"),
            "member_kind": cohort.get("member_kind"),
            "size": cohort.get("size"),
            "description": (cohort.get("definition", {}) or {}).get("description"),
        }),
        table("Population Analytics (blocks)", ["subject", "count", "distributions"], blocks_rows),
        table("Trend Reports", ["metric", "direction", "delta", "points"], trend_rows),
        table("Quality Reports", ["metric", "value", "num", "den"], quality_rows),
        validation_badges("Analytics Validation", intel.get("analytics", {}).get("validation", {})),
        validation_badges("Trend Validation", intel.get("trend", {}).get("validation", {})),
        validation_badges("Quality Validation", intel.get("quality", {}).get("validation", {})),
        badges("Intelligence Audit", [("audit_verified", audit.get("verified", False))]),
    ]
    viz = [population_analytics(analytics), trend_analysis(trend), quality_metrics(quality)]
    return [Page("intelligence", "Intelligence", sections, viz)]
