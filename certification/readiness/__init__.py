"""``certification/readiness`` — per-phase readiness-state determination (P10).

Maps the collected evidence onto each of the nine phases and determines, from facts only,
their operational / validation / readiness / gap state. The states are a closed vocabulary;
nothing here is assumed — every state is derived from a scorecard, health check, or
end-to-end result in the evidence bundle.
"""

from __future__ import annotations

from ..version import CERTIFICATION_READINESS_VERSION

# operational / validation / readiness states
OPERATIONAL, NOT_OPERATIONAL = "OPERATIONAL", "NOT_OPERATIONAL"
VALIDATED, NOT_VALIDATED = "VALIDATED", "NOT_VALIDATED"
READY, NOT_READY = "READY", "NOT_READY"
# gap states
GAP_NONE, GAP_MINOR, GAP_MAJOR, GAP_CRITICAL = "NONE", "MINOR", "MAJOR", "CRITICAL"

# phase -> the validation scorecard key that measures it (Validation is its own completeness)
PHASES = [
    ("EEG Foundation", "eeg_readiness"),
    ("Signal Processing", "signal_processing_readiness"),
    ("Feature Engineering", "feature_engineering_readiness"),
    ("Model Foundation", "model_readiness"),
    ("Inference", "inference_readiness"),
    ("Backend", "backend_readiness"),
    ("Frontend", "frontend_readiness"),
    ("Operations", "operations_readiness"),
    ("Validation", None),
]

# Inherited / disclosed gaps per phase (deployment-scoped, not technical-defect).
_PHASE_GAPS = {
    "EEG Foundation": (GAP_MAJOR, "validated on synthetic/deterministic fixtures only (G1)"),
    "Model Foundation": (GAP_MAJOR, "untuned reference baselines on synthetic data; not clinically tuned (G1)"),
    "Inference": (GAP_MINOR, "predictions reflect untuned baselines (G1)"),
    "Operations": (GAP_MAJOR, "in-memory persistence; no durable database (G3)"),
}


def determine_phase_states(bundle: dict) -> dict:
    scorecards = bundle["validation"]["scorecards"]["scorecards"]
    validation_complete = bundle["validation"].get("validation_complete", False)
    e2e_ok = bundle["e2e"].get("ok", False)
    health = bundle["operations_health"].get("components", {})

    states = {}
    for phase, key in PHASES:
        if key is None:                      # Validation phase
            ready = bool(validation_complete)
            operational = ready
            validated = ready
        else:
            card = scorecards.get(key, {})
            ready = bool(card.get("ready"))
            operational = ready
            validated = ready
        gap_sev, gap_detail = _PHASE_GAPS.get(phase, (GAP_NONE, ""))
        states[phase] = {
            "operational_state": OPERATIONAL if operational else NOT_OPERATIONAL,
            "validation_state": VALIDATED if validated else NOT_VALIDATED,
            "readiness_state": READY if ready else NOT_READY,
            "gap_state": gap_sev, "gap_detail": gap_detail,
        }
    # backend/frontend additionally corroborated by live health + e2e
    states["Backend"]["operational_state"] = (
        OPERATIONAL if (health.get("backend", {}).get("healthy") and e2e_ok) else NOT_OPERATIONAL)
    states["Frontend"]["operational_state"] = (
        OPERATIONAL if health.get("frontend", {}).get("healthy") else NOT_OPERATIONAL)
    return {"readiness_version": CERTIFICATION_READINESS_VERSION, "phases": states}


__all__ = ["determine_phase_states", "PHASES", "OPERATIONAL", "VALIDATED", "READY", "NOT_READY",
           "GAP_NONE", "GAP_MINOR", "GAP_MAJOR", "GAP_CRITICAL"]
