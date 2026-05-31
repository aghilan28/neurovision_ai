"""Product readiness audit (P10-B).

Audits each of the nine phases and emits readiness / risk / gap / evidence findings from
the per-phase states derived from the evidence bundle. Evidence only.
"""

from __future__ import annotations

from ..readiness import determine_phase_states, READY, GAP_NONE
from ..util import fingerprint
from ..version import CERTIFICATION_AUDIT_VERSION


class ProductReadinessAudit:
    def run(self, bundle: dict) -> dict:
        phase_states = determine_phase_states(bundle)["phases"]
        readiness_findings, risk_findings, gap_findings, evidence_findings = [], [], [], []

        for phase, st in phase_states.items():
            ready = st["readiness_state"] == READY
            readiness_findings.append({"phase": phase, "ready": ready,
                                       "operational": st["operational_state"],
                                       "validation": st["validation_state"]})
            if not ready:
                risk_findings.append({"phase": phase, "severity": "HIGH",
                                      "finding": f"{phase} is not READY"})
            if st["gap_state"] != GAP_NONE:
                gap_findings.append({"phase": phase, "severity": st["gap_state"],
                                     "finding": st["gap_detail"]})
            evidence_findings.append({"phase": phase, "evidence": st})

        operational = all(s["operational_state"] == "OPERATIONAL" for s in phase_states.values())
        validated = all(s["validation_state"] == "VALIDATED" for s in phase_states.values())
        all_ready = all(s["readiness_state"] == READY for s in phase_states.values())
        return {
            "audit_version": CERTIFICATION_AUDIT_VERSION,
            "operational_state": operational, "validation_state": validated,
            "readiness_state": all_ready,
            "n_phases": len(phase_states),
            "phase_states": phase_states,
            "readiness_findings": readiness_findings, "risk_findings": risk_findings,
            "gap_findings": gap_findings, "evidence_findings": evidence_findings,
            "signature": fingerprint({p: s["readiness_state"] for p, s in phase_states.items()}),
        }


__all__ = ["ProductReadinessAudit"]
