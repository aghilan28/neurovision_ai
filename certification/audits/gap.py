"""Gap analysis (P10-F).

Determines, from evidence, what exists / is partial / is missing, classifies each gap
(CRITICAL / MAJOR / MINOR / INFORMATIONAL), and flags whether it blocks deployment — for a
non-clinical (research/engineering) deployment vs an unconditioned clinical deployment.
Evidence only.
"""

from __future__ import annotations

from ..util import fingerprint
from ..version import CERTIFICATION_GAP_VERSION

CRITICAL, MAJOR, MINOR, INFORMATIONAL = "CRITICAL", "MAJOR", "MINOR", "INFORMATIONAL"
EXISTS, PARTIAL, MISSING = "EXISTS", "PARTIAL", "MISSING"


class GapAnalysis:
    def run(self, bundle: dict) -> dict:
        gaps = []

        def gap(gid, item, state, severity, detail, blocks_clinical=False, blocks_nonclinical=False):
            gaps.append({"id": gid, "item": item, "state": state, "severity": severity,
                         "detail": detail, "blocks_clinical_deployment": blocks_clinical,
                         "blocks_nonclinical_deployment": blocks_nonclinical})

        # --- what exists (evidence-confirmed) ---
        phases_ready = bundle["validation"]["scorecards"]["scorecards"]
        for key, card in phases_ready.items():
            if key == "overall_product_readiness":
                continue
            if card.get("ready"):
                gap(f"GAP-EXISTS-{key}", key.replace("_readiness", ""), EXISTS, INFORMATIONAL,
                    "implemented, validated, and ready (evidence: P9 scorecard)")

        # --- what is partial ---
        gap("GAP-DATA", "real clinical data path", PARTIAL, MAJOR,
            "real EEG can be ingested (P1), but models are trained/validated on synthetic "
            "fixtures only (G1)", blocks_clinical=True)
        gap("GAP-PERSIST", "durable persistence", PARTIAL, MAJOR,
            "content-addressed on-disk stores + backups exist, but registries are in-memory; "
            "no database (G3)", blocks_clinical=True)
        gap("GAP-SERVE", "online serving transport", PARTIAL, MINOR,
            "in-process API + CLI exist; no long-running HTTP service")

        # --- what is missing ---
        gap("GAP-CLINICAL", "clinical validation", MISSING, CRITICAL,
            "no clinical/prospective validation has been performed (out of program scope)",
            blocks_clinical=True)
        gap("GAP-SECHARD", "production security hardening", MISSING, MAJOR,
            "no TLS/rate-limiting/IdP; auth is local PBKDF2 with injectable secrets",
            blocks_clinical=True)
        gap("GAP-GOV", "mechanized governance", MISSING, MINOR,
            "governance documented (ADRs) but not enforced in CI (G2)")

        def _by(states):
            return [g["id"] for g in gaps if g["state"] in states]

        blockers_clinical = [g["id"] for g in gaps if g["blocks_clinical_deployment"]]
        blockers_nonclinical = [g["id"] for g in gaps if g["blocks_nonclinical_deployment"]]
        by_sev = {s: [g["id"] for g in gaps if g["severity"] == s]
                  for s in (CRITICAL, MAJOR, MINOR, INFORMATIONAL)}
        return {
            "gap_version": CERTIFICATION_GAP_VERSION,
            "n_gaps": len(gaps),
            "exists": _by({EXISTS}), "partial": _by({PARTIAL}), "missing": _by({MISSING}),
            "by_severity": by_sev,
            "blocks_clinical_deployment": blockers_clinical,
            "blocks_nonclinical_deployment": blockers_nonclinical,
            "gaps": gaps,
            "signature": fingerprint([(g["id"], g["state"], g["severity"]) for g in gaps]),
        }


__all__ = ["GapAnalysis", "CRITICAL", "MAJOR", "MINOR", "INFORMATIONAL", "EXISTS", "PARTIAL", "MISSING"]
