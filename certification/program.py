"""``certification.program`` — the end-to-end certification run (P10).

Collects evidence once, runs every audit, builds the scorecards, renders the decision, and
assembles the reports. This is what ``scripts/verify_productization_p10`` and the e2e test
drive. It evaluates only; it modifies nothing.
"""

from __future__ import annotations

from typing import Optional

from .audits import ProductReadinessAudit, RiskAssessment, GapAnalysis
from .deployment import DeploymentReadinessAudit
from .decision import DecisionEngine
from .evidence import EvidenceCollector
from .reports import build_all_reports
from .scorecards import build_scorecards
from .util import fingerprint
from .version import CERTIFICATION_PROGRAM_VERSION


def run_certification(fixtures: dict, *, validation_kwargs: Optional[dict] = None,
                      workspace_dir: Optional[str] = None) -> dict:
    """Run the full P10 certification program against the real platform; return the result."""
    bundle = EvidenceCollector().collect(fixtures, validation_kwargs=validation_kwargs,
                                         workspace_dir=workspace_dir)

    product_audit = ProductReadinessAudit().run(bundle)
    deployment_audit = DeploymentReadinessAudit().run(bundle)
    risk = RiskAssessment().run(bundle)
    gap = GapAnalysis().run(bundle)
    scorecards = build_scorecards(bundle, product_audit=product_audit,
                                 deployment_audit=deployment_audit, risk=risk, gap=gap)
    decision = DecisionEngine().decide(
        bundle=bundle, product_audit=product_audit, deployment_audit=deployment_audit,
        risk=risk, gap=gap, scorecards=scorecards)
    reports = build_all_reports(
        bundle=bundle, product_audit=product_audit, deployment_audit=deployment_audit,
        risk=risk, gap=gap, scorecards=scorecards, decision=decision)

    return {
        "certification_program_version": CERTIFICATION_PROGRAM_VERSION,
        "evidence": bundle, "product_audit": product_audit, "deployment_audit": deployment_audit,
        "risk": risk, "gap": gap, "scorecards": scorecards, "decision": decision, "reports": reports,
        "verdict": decision["verdict"],
        "signature": fingerprint({"decision": decision["signature"],
                                  "scorecards": scorecards["signature"],
                                  "product": product_audit["signature"]}),
    }


__all__ = ["run_certification"]
