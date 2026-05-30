"""Build the Clinical Workstation snapshot (V2-P7).

This is the **only** seam between the backend domain subsystems and the frontend
presentation layer. It composes the real V2 services (Cases, Reviews, Findings,
Knowledge, Multi-Case Intelligence, Decision Support) over **one shared lineage
tracker**, runs a small deterministic multi-case workflow, and serializes every
*registered artifact* — registries, reports, immutable audit logs, the lineage
graph, validation results — into a single JSON snapshot.

The frontend (``frontend/clinical_workstation``) reads that snapshot with stdlib
``json`` only and imports **no** domain module (NR-8). Scripts may import any
layer; this is the sanctioned composition point (like ``run_clinical_workflow``).

    python -m scripts.build_workstation_snapshot --out workstation_snapshot.json

The snapshot is deterministic (DETERMINISTIC_EPOCH everywhere; no wall-clock),
so the same inputs always produce a byte-identical file.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Optional

from backend.clinical_cases import CaseService, CaseStatus
from backend.clinical_review import ReviewService
from backend.clinical_findings import FindingService, FindingRecord, evidence_spec
from backend.clinical_knowledge import KnowledgeService
from backend.multi_case_intelligence import (
    MultiCaseIntelligenceService, PopulationBuilder,
    CohortDefinition, CohortCriterion, CohortKind,
)
from backend.decision_support import DecisionSupportService

SNAPSHOT_VERSION = "workstation-snapshot@1.0.0"


# --------------------------------------------------------------------------- #
# Serialization helpers (registered artifacts only)
# --------------------------------------------------------------------------- #
def _audit(log) -> dict:
    """Serialize an ImmutableAuditLog (+ its verified flag)."""
    d = log.to_dict()
    d["verified"] = log.verify()
    return d


def _case_block(cs: CaseService, case) -> dict:
    return {
        "case_id": case.case_id,
        "patient_id": case.patient_id,
        "registry_record": cs.registry.get(case.case_id).to_dict(),
        "reports": cs.reports(case),
        "validation": cs.validate(case).to_dict(),
        "audit": _audit(cs.audit_log_for(case.case_id)),
        "lineage_id": case.lineage_id,
        "lineage_verified": cs.lineage.verify_chain(case.lineage_id),
        "studies": [s.study_id for s in case.studies],
    }


def _review_block(rs: ReviewService, review) -> dict:
    return {
        "review_id": review.review_id,
        "case_id": review.case_id,
        "registry_record": rs.registry.get(review.review_id).to_dict(),
        "reports": rs.reports(review),
        "validation": rs.validate(review).to_dict(),
        "tracking": rs.tracking(review),
        "audit": _audit(rs.audit_log_for(review.review_id)),
        "lineage_id": review.lineage_id,
        "lineage_verified": rs.lineage.verify_chain(review.lineage_id),
    }


def _finding_block(fs: FindingService, finding) -> dict:
    interp_store = fs.interpretation_store()
    interps = [interp_store[i].to_dict() for i in finding.interpretation_ids if i in interp_store]
    return {
        "finding_id": finding.finding_id,
        "case_id": finding.case_id,
        "review_id": finding.review_id,
        "registry_record": fs.registry.get(finding.finding_id).to_dict(),
        "reports": fs.reports(finding),
        "validation": fs.validate(finding).to_dict(),
        "audit": _audit(fs.audit_log_for(finding.finding_id)),
        "interpretations": interps,
        "lineage_id": finding.lineage_id,
        "lineage_verified": fs.lineage.verify_chain(finding.lineage_id),
    }


def _knowledge_block(ks: KnowledgeService) -> dict:
    return {
        "registry": ks.registry.to_dict(),
        "terminology": ks.terminology.to_dict(),
        "concepts": ks.concepts.to_dict(),
        "taxonomy": ks.taxonomy.to_dict(),
        "relationships": ks.relationships.to_dict(),
        "reports": ks.reports(),
        "validation": ks.validate().to_dict(),
        "audit": _audit(ks.audit),
    }


def _intel_artifact(art, kind: str, mci: MultiCaseIntelligenceService, *,
                    population=None, baseline=None) -> dict:
    return {
        "kind": kind,
        "artifact": art.to_dict(),
        "validation": mci.validate(art, kind, population=population,
                                   baseline_digest=baseline).to_dict(),
    }


def _decision_artifact(art, kind: str, ds: DecisionSupportService, *,
                       population=None, baseline=None) -> dict:
    return {
        "kind": kind,
        "artifact": art.to_dict(),
        "validation": ds.validate(art, kind, population=population,
                                  baseline_digest=baseline).to_dict(),
    }


# --------------------------------------------------------------------------- #
# Snapshot assembly
# --------------------------------------------------------------------------- #
def build_snapshot(*, n_cases: int = 3, reviewer: str = "dr.reviewer") -> dict:
    """Compose the real V2 services over one lineage tracker and serialize them.

    Returns a plain JSON-able dict — the Clinical Workstation snapshot.
    """
    cs = CaseService()
    tracker = cs.lineage  # ONE shared lineage tracker across all subsystems
    ks = KnowledgeService(lineage_tracker=tracker).seed_default_knowledge()
    rs = ReviewService(lineage_tracker=tracker)
    fs = FindingService(lineage_tracker=tracker)

    # Fixed, deterministic case plan: (patient, category, confidence, finalize, interp).
    plan = [
        ("PT-001", "LPD", 0.91, True, True),
        ("PT-002", "GRDA", 0.34, False, False),
        ("PT-003", "GPD", 0.62, True, True),
        ("PT-004", "unknown_pattern", 0.80, False, False),
        ("PT-005", "SZ", 0.88, True, True),
    ][:n_cases]

    cases, reviews, findings = [], [], []
    pb = PopulationBuilder()

    for i, (patient, category, conf, finalize, add_interp) in enumerate(plan):
        case = cs.create_case(patient_key=patient, case_key=f"ENC-{i:03d}", owner="clinical-ops")
        cs.transition(case, CaseStatus.INGESTED, "EEG ingested")
        cs.transition(case, CaseStatus.PROCESSING, "intelligence computed")
        cs.transition(case, CaseStatus.READY_FOR_REVIEW, "ready for review")

        review = rs.create_review(case_id=case.case_id, case_lineage_id=case.lineage_id,
                                  study_id=None, inference_lineage_id=None, artifact_refs=())
        rs.assign(review, assignee=reviewer, priority="routine", reason="triage")
        cs.transition(case, CaseStatus.UNDER_REVIEW, "review started")
        review, sess = rs.start_session(review)

        finding = fs.create_finding(
            review_id=review.review_id, case_id=case.case_id, study_id=None,
            record=FindingRecord(observation=category, category=category),
            evidence_specs=[
                evidence_spec("inference", f"inf-{i}", "output-contract@1.0.0", confidence=conf),
                evidence_spec("coverage", f"cov-{i}", "coverage@1.0.0", confidence=min(0.99, conf + 0.03)),
            ],
            review_lineage_id=review.lineage_id)
        if add_interp:
            finding, _ = fs.add_interpretation(finding, text=f"{category} pattern",
                                               confidence_level="high" if conf > 0.7 else "moderate")
            finding = fs.to_draft(finding)
            finding = fs.submit_for_review(finding)
            finding = fs.confirm(finding)
        if finalize:
            review, sess = rs.end_session(review, sess, outcome="confirmed", notes="reviewed")
            rs.submit_for_confirmation(review)
            rs.complete(review)
            cs.transition(case, CaseStatus.REVIEWED, "review complete")

        cases.append(case)
        reviews.append(review)
        findings.append(finding)
        pb.add_case(case).add_review(review).add_finding(finding)

    # Interpretations for the population view.
    for interp in fs.interpretation_store().values():
        pb.add_interpretation(interp)
    pb.add_knowledge_service(ks)
    population = pb.build()
    baseline = population.integrity_digest()

    # --- V2-P5 Multi-Case Intelligence -----------------------------------
    mci = MultiCaseIntelligenceService(lineage_tracker=tracker)
    intel = mci.run_full_intelligence(population)
    cohort = mci.build_cohort(population, CohortDefinition(
        member_kind=CohortKind.FINDING,
        criteria=(CohortCriterion("known_category", "eq", True),),
        description="findings whose category is in the knowledge vocabulary"))
    cohort_analytics = mci.build_cohort_analytics(population, cohort)

    intelligence_block = {
        "registry": mci.registry.to_dict(),
        "audit": _audit(mci.audit),
        "cohort": {"artifact": cohort.to_dict(),
                   "validation": mci.validate(cohort, "cohort", population=population,
                                              baseline_digest=baseline).to_dict()},
        "cohort_analytics": _intel_artifact(cohort_analytics, "analytics", mci,
                                            population=population, baseline=baseline),
        "analytics": _intel_artifact(intel["analytics"], "analytics", mci,
                                     population=population, baseline=baseline),
        "trend": _intel_artifact(intel["trend"], "trend", mci,
                                 population=population, baseline=baseline),
        "quality": _intel_artifact(intel["quality"], "quality", mci,
                                   population=population, baseline=baseline),
        "summary": _intel_artifact(intel["summary"], "intel_report", mci,
                                   population=population, baseline=baseline),
    }

    # --- V2-P6 Decision Support ------------------------------------------
    ds = DecisionSupportService(lineage_tracker=tracker)
    decision_bundles = []
    kinds = ["decision_context", "evidence_bundle", "risk_context", "prioritization",
             "guidance", "decision_support"]
    for case in cases:
        bundle = ds.process_case(population, case.case_id,
                                 population_analytics=intel["analytics"].artifact
                                 if hasattr(intel["analytics"], "artifact") else intel["analytics"])
        artifacts = {k: _decision_artifact(a, k, ds, population=population, baseline=baseline)
                     for k, a in zip(kinds, bundle.artifacts())}
        decision_bundles.append({
            "case_id": case.case_id,
            "record_id": bundle.decision_support.record_id,
            "artifacts": artifacts,
            "reports": ds.reports(bundle),
        })

    decision_block = {
        "registry": ds.registry.to_dict(),
        "audit": _audit(ds.audit),
        "bundles": decision_bundles,
    }

    # --- shared lineage + cross-cutting ----------------------------------
    lineage_block = tracker.to_dict()
    # A representative end-to-end chain (patient -> decision_support) for the explorer.
    rep_chain = []
    if decision_bundles:
        rep_lid = ds.registry.get(decision_bundles[0]["record_id"]).lineage_id
        rep_chain = [r.to_dict() for r in tracker.chain(rep_lid)]
        rep_chain_verified = tracker.verify_chain(rep_lid)
    else:
        rep_chain_verified = True

    snapshot = {
        "snapshot_version": SNAPSHOT_VERSION,
        "source": "registered artifacts only (composed by scripts.build_workstation_snapshot)",
        "meta": {
            "n_cases": len(cases),
            "n_reviews": len(reviews),
            "n_findings": len(findings),
            "patients": population.patient_ids(),
            "source_integrity_digest": baseline,
        },
        "cases": [_case_block(cs, c) for c in cases],
        "reviews": [_review_block(rs, r) for r in reviews],
        "findings": [_finding_block(fs, f) for f in findings],
        "knowledge": _knowledge_block(ks),
        "intelligence": intelligence_block,
        "decision_support": decision_block,
        "lineage": lineage_block,
        "representative_chain": {"records": rep_chain, "verified": rep_chain_verified},
        "registries": {
            "case_registry": cs.registry.to_dict(),
            "review_registry": rs.registry.to_dict(),
            "finding_registry": fs.registry.to_dict(),
            "knowledge_registry": ks.registry.to_dict(),
            "intelligence_registry": mci.registry.to_dict(),
            "decision_registry": ds.registry.to_dict(),
        },
    }
    return snapshot


def write_snapshot(out_path: str, *, n_cases: int = 3) -> str:
    snapshot = build_snapshot(n_cases=n_cases)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, sort_keys=True, separators=(",", ":"))
    return out_path


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description="Build the Clinical Workstation snapshot (V2-P7).")
    p.add_argument("--out", default="workstation_snapshot.json")
    p.add_argument("--cases", type=int, default=3)
    args = p.parse_args(argv)
    path = write_snapshot(args.out, n_cases=args.cases)
    snap = build_snapshot(n_cases=args.cases)
    print(f"wrote {path}")
    print(f"snapshot_version : {snap['snapshot_version']}")
    print(f"cases/reviews/findings : {snap['meta']['n_cases']}/"
          f"{snap['meta']['n_reviews']}/{snap['meta']['n_findings']}")
    print(f"representative chain verified : {snap['representative_chain']['verified']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
