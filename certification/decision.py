"""``certification.decision`` — the production decision engine (P10-I).

Produces exactly one evidence-based verdict — CERTIFIED / CONDITIONALLY CERTIFIED /
NOT CERTIFIED — from deterministic rules over the audits + evidence, and cites the
readiness, risks, gaps, validation, operations, and deployment that drove it. No
assumptions, no optimism, no future promises.

Decision rules (in order):
  1. NOT CERTIFIED  — if technical foundation fails (end-to-end, validation, compliance,
     operations health/validation, or any phase not operationally ready), or any gap blocks
     even a non-clinical deployment, or any unmitigated CRITICAL non-clinical risk exists.
  2. CERTIFIED      — technical foundation holds AND deployment is fully ready AND there are
     no clinical-blocking gaps and no CRITICAL/HIGH residual conditions.
  3. CONDITIONALLY CERTIFIED — technical foundation holds and the product is deployable as a
     research/engineering (non-clinical) system, but disclosed conditions must be met before
     unconditioned clinical production.
"""

from __future__ import annotations

from .util import fingerprint
from .version import (
    CERTIFICATION_DECISION_VERSION, CERTIFIED, CONDITIONALLY_CERTIFIED, NOT_CERTIFIED,
)


class DecisionEngine:
    def decide(self, *, bundle: dict, product_audit: dict, deployment_audit: dict,
               risk: dict, gap: dict, scorecards: dict) -> dict:
        v = bundle["validation"]

        technical_foundation = all([
            bool(bundle["e2e"]["ok"]),
            bool(v.get("validation_complete")),
            bool(bundle["compliance"]["ok"]),
            bool(bundle["operations_validation"].get("ok")),
            bool(bundle["operations_health"].get("healthy")),
            bool(product_audit["operational_state"]),
            bool(product_audit["readiness_state"]),
        ])

        nonclinical_blockers = list(gap["blocks_nonclinical_deployment"])
        open_critical_nonclinical = list(risk["open_critical_non_clinical"])
        clinical_blockers = list(gap["blocks_clinical_deployment"])
        deployment_conditions = list(deployment_audit["not_ready_areas"])
        residual_clinical_risks = [r["id"] for r in risk["risks"]
                                   if r["clinical_deployment_only"] and r["severity"] in ("CRITICAL", "HIGH")]

        citations = {
            "readiness": {"all_phases_ready": product_audit["readiness_state"],
                          "overall_score": scorecards["overall_score"]},
            "risks": {"critical": risk["critical"], "high": risk["high"],
                      "open_critical_non_clinical": open_critical_nonclinical},
            "gaps": {"blocks_clinical": clinical_blockers,
                     "blocks_nonclinical": nonclinical_blockers},
            "validation": {"validation_complete": v.get("validation_complete"),
                           "reproducible": v["reproducibility"].get("ok")},
            "operations": {"health": bundle["operations_health"].get("healthy"),
                           "validation": bundle["operations_validation"].get("ok")},
            "deployment": {"ready": deployment_audit["ready"],
                           "not_ready_areas": deployment_conditions},
        }

        if not technical_foundation or nonclinical_blockers or open_critical_nonclinical:
            verdict = NOT_CERTIFIED
            rationale = ("The technical foundation is not fully met, or an unmitigated "
                         "critical non-clinical risk / non-clinical deployment blocker exists.")
            conditions = sorted(set(nonclinical_blockers + open_critical_nonclinical))
            go = "NO-GO"
            scope = "Deployment must not proceed until the cited blockers are resolved."
        elif not clinical_blockers and not deployment_conditions and not residual_clinical_risks:
            verdict = CERTIFIED
            rationale = ("All phases are ready and validated, deployment is fully ready, and "
                         "no residual blocking gaps or risks remain.")
            conditions = []
            go = "GO"
            scope = "Deployment may proceed."
        else:
            verdict = CONDITIONALLY_CERTIFIED
            rationale = ("The platform is technically validated, operationally ready, and "
                         "deployable as a research/engineering (non-clinical) system. Disclosed "
                         "conditions must be met before unconditioned clinical production.")
            conditions = sorted(set(clinical_blockers + deployment_conditions + residual_clinical_risks))
            go = "GO (conditional)"
            scope = ("GO for non-clinical / research / engineering deployment under the stated "
                     "conditions; NO-GO for unconditioned clinical production until the "
                     "conditions are closed.")

        decision = {
            "decision_version": CERTIFICATION_DECISION_VERSION,
            "verdict": verdict,
            "go_no_go": go,
            "scope": scope,
            "rationale": rationale,
            "conditions": conditions,
            "citations": citations,
        }
        decision["signature"] = fingerprint({"verdict": verdict, "conditions": conditions,
                                             "citations": citations})
        return decision


__all__ = ["DecisionEngine"]
