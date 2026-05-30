"""``backend/clinical_findings/evidence`` — finding evidence system (V2-P3).

Links findings to registered V1/V2 artifacts (inference/calibration/conformal/
coverage/risk outputs, artifacts, reports, review actions). A finding must never
exist without evidence; this subsystem builds the typed, versioned, traceable
``FindingEvidence`` links.
"""

from __future__ import annotations

from .evidence import EvidenceManager, VALID_EVIDENCE_TYPES, EvidenceError, evidence_spec

__all__ = ["EvidenceManager", "VALID_EVIDENCE_TYPES", "EvidenceError", "evidence_spec"]
