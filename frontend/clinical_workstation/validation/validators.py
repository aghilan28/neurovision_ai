"""Workstation validation — consistency checks over the loaded snapshot.

These are *presentation-integrity* checks: they confirm the workstation is showing
a coherent, fully-traceable, fully-registered view, and that every value it shows
came from a registered artifact. They do not recompute domain truth — they read the
validation/audit/lineage results the backend already recorded.

Checks (the seven mandated consistency dimensions):
  * artifact_consistency   — every displayed entity resolves to a registry record.
  * registry_consistency   — registry counts agree with the displayed collections.
  * version_consistency    — every entity carries a version; intelligence/decision
                             artifact validations report version_integrity ok.
  * audit_consistency      — every audit log verifies (tamper-evident chains).
  * lineage_consistency    — per-entity lineage verifies + the end-to-end chain verifies.
  * workflow_consistency   — the Patient→…→Decision Support chain kinds are all present.
  * state_consistency      — navigation context references only existing artifacts.
"""

from __future__ import annotations

from ..schemas import ValidationReport

_CHAIN_KINDS = ["patient", "case", "review", "finding", "interpretation",
                "concept", "analytics", "decision_support"]


def _all(items, pred) -> bool:
    return all(pred(x) for x in items) if items else True


def validate_state(state) -> ValidationReport:
    report = ReportBuilder(state)
    report.artifact_consistency()
    report.registry_consistency()
    report.version_consistency()
    report.audit_consistency()
    report.lineage_consistency()
    report.workflow_consistency()
    report.state_consistency()
    return report.report


class ReportBuilder:
    def __init__(self, state) -> None:
        self.state = state
        self.report = ValidationReport()

    # --- artifact consistency -------------------------------------------------
    def artifact_consistency(self) -> None:
        s = self.state
        ok = (_all(s.cases, lambda c: bool(c.get("registry_record")))
              and _all(s.reviews, lambda r: bool(r.get("registry_record")))
              and _all(s.findings, lambda f: bool(f.get("registry_record"))))
        self.report.add("artifact_consistency", ok,
                        "every displayed entity has a registry record" if ok
                        else "an entity is missing its registry record")

    # --- registry consistency -------------------------------------------------
    def registry_consistency(self) -> None:
        s = self.state
        creg = s.registries.get("case_registry", {})
        rreg = s.registries.get("review_registry", {})
        freg = s.registries.get("finding_registry", {})
        checks = []
        if "n_records" in creg or "cases" in creg:
            checks.append(_count(creg, "cases") == len(s.cases))
        if "reviews" in rreg or "n_records" in rreg:
            checks.append(_count(rreg, "reviews") == len(s.reviews))
        if "findings" in freg or "n_records" in freg:
            checks.append(_count(freg, "findings") == len(s.findings))
        ok = all(checks) if checks else True
        self.report.add("registry_consistency", ok,
                        "registry counts agree with displayed collections" if ok
                        else "registry counts disagree with displayed collections")

    # --- version consistency --------------------------------------------------
    def version_consistency(self) -> None:
        s = self.state
        entity_versions = (_all(s.cases, lambda c: bool(c.get("registry_record", {}).get("version")))
                           and _all(s.reviews, lambda r: bool(r.get("registry_record", {}).get("version")))
                           and _all(s.findings, lambda f: bool(f.get("registry_record", {}).get("version"))))
        intel = s.intelligence
        intel_ok = all(_validation_ok(intel.get(k, {}).get("validation", {}))
                       for k in ("analytics", "trend", "quality") if intel.get(k))
        self.report.add("version_consistency", entity_versions and intel_ok,
                        "all entities versioned; intelligence validations ok" if (entity_versions and intel_ok)
                        else "missing version or failing intelligence validation")

    # --- audit consistency ----------------------------------------------------
    def audit_consistency(self) -> None:
        s = self.state
        ok = (_all(s.cases, lambda c: c.get("audit", {}).get("verified", False))
              and _all(s.reviews, lambda r: r.get("audit", {}).get("verified", False))
              and _all(s.findings, lambda f: f.get("audit", {}).get("verified", False))
              and (s.knowledge.get("audit", {}).get("verified", True))
              and (s.intelligence.get("audit", {}).get("verified", True))
              and (s.decision_support.get("audit", {}).get("verified", True)))
        self.report.add("audit_consistency", ok,
                        "every audit log verifies" if ok else "an audit log failed verification")

    # --- lineage consistency --------------------------------------------------
    def lineage_consistency(self) -> None:
        s = self.state
        per_entity = (_all(s.cases, lambda c: c.get("lineage_verified", False))
                      and _all(s.reviews, lambda r: r.get("lineage_verified", False))
                      and _all(s.findings, lambda f: f.get("lineage_verified", False)))
        chain = s.representative_chain.get("verified", False)
        self.report.add("lineage_consistency", per_entity and chain,
                        "per-entity + end-to-end lineage verifies" if (per_entity and chain)
                        else "a lineage chain failed verification")

    # --- workflow consistency -------------------------------------------------
    def workflow_consistency(self) -> None:
        """The mandated kinds all exist in the shared lineage graph, and the
        end-to-end decision chain (its spine) verifies.

        ``concept`` (Knowledge) and ``analytics`` (Intelligence) are *parallel*
        provenance branches — they are not ancestors of a single decision node —
        so presence is checked against the whole lineage graph, while the
        representative chain proves the Patient→…→Decision Support spine."""
        s = self.state
        graph_kinds = {rec.get("kind") for rec in s.lineage.get("records", {}).values()}
        chain_kinds = {r.get("kind") for r in s.representative_chain.get("records", [])}
        present = graph_kinds | chain_kinds
        missing = [k for k in _CHAIN_KINDS if k not in present]
        chain_ok = s.representative_chain.get("verified", False)
        ok = (not missing) and chain_ok
        detail = ("Patient→…→Decision Support workflow present + spine verified" if ok
                  else f"missing kinds={missing} chain_verified={chain_ok}")
        self.report.add("workflow_consistency", ok, detail)

    # --- state consistency ----------------------------------------------------
    def state_consistency(self) -> None:
        s = self.state
        ctx = s.context_snapshot()
        problems = []
        if ctx.get("current_case") and not s.case(ctx["current_case"]):
            problems.append("current_case")
        if ctx.get("current_review") and not s.review(ctx["current_review"]):
            problems.append("current_review")
        if ctx.get("current_finding") and not s.finding(ctx["current_finding"]):
            problems.append("current_finding")
        self.report.add("state_consistency", not problems,
                        "navigation context references existing artifacts" if not problems
                        else f"dangling context: {problems}")


def _count(registry: dict, collection_key: str) -> int:
    if collection_key in registry and isinstance(registry[collection_key], dict):
        return len(registry[collection_key])
    return registry.get("n_records", registry.get(f"n_{collection_key}", -1))


def _validation_ok(validation: dict) -> bool:
    return bool(validation.get("ok", False)) if validation else True
