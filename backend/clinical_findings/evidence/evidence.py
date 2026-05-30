"""Evidence construction for findings.

Builders mint deterministic evidence ids and produce immutable ``FindingEvidence``
values that point at *registered* artifacts (a V1 inference output/contract, a
checksummed artifact, a registered report, or a review action). Evidence
confidence, when present, is a **recorded** value (e.g. a calibrated confidence or
coverage figure) — the findings layer never computes or assumes it.
"""

from __future__ import annotations

from typing import Optional

from ..version import FINDING_EVIDENCE_VERSION
from ..models.domain import FindingEvidence
from ..identity import mint_evidence

VALID_EVIDENCE_TYPES = (
    "inference", "calibration", "conformal", "coverage", "risk",
    "artifact", "report", "review_action",
)


class EvidenceError(ValueError):
    """Raised on invalid evidence construction."""


class EvidenceManager:
    """Stateless builders that produce immutable ``FindingEvidence`` values."""

    @staticmethod
    def build(*, finding_id: str, evidence_type: str, evidence_source: str,
              evidence_version: str, evidence_confidence: Optional[float] = None,
              lineage_id: Optional[str] = None, notes: str = "") -> FindingEvidence:
        if evidence_type not in VALID_EVIDENCE_TYPES:
            raise EvidenceError(f"evidence_type must be one of {VALID_EVIDENCE_TYPES}")
        if not evidence_source:
            raise EvidenceError("evidence_source must reference a registered artifact")
        if not evidence_version:
            raise EvidenceError("evidence_version must be recorded (contract version / checksum)")
        eid = mint_evidence(finding_id, f"{evidence_type}:{evidence_source}").id
        return FindingEvidence(
            evidence_id=eid, finding_id=finding_id, evidence_type=evidence_type,
            evidence_source=evidence_source, evidence_version=evidence_version,
            evidence_confidence=evidence_confidence, lineage_id=lineage_id, notes=notes,
            evidence_version_tag=FINDING_EVIDENCE_VERSION)

    # --- convenience builders for V1 registered outputs/artifacts -------------
    @staticmethod
    def from_inference_output(*, finding_id: str, output_type: str, inference_id: str,
                              output_version: str, confidence: Optional[float] = None,
                              lineage_id: Optional[str] = None) -> FindingEvidence:
        if output_type not in ("inference", "calibration", "conformal", "coverage", "risk"):
            raise EvidenceError(f"unsupported inference output_type {output_type!r}")
        return EvidenceManager.build(
            finding_id=finding_id, evidence_type=output_type, evidence_source=inference_id,
            evidence_version=output_version, evidence_confidence=confidence, lineage_id=lineage_id)

    @staticmethod
    def from_artifact(*, finding_id: str, artifact_name: str, checksum: str,
                      lineage_id: Optional[str] = None) -> FindingEvidence:
        return EvidenceManager.build(
            finding_id=finding_id, evidence_type="artifact", evidence_source=artifact_name,
            evidence_version=checksum, lineage_id=lineage_id)

    @staticmethod
    def from_report(*, finding_id: str, report_name: str, report_version: str,
                    lineage_id: Optional[str] = None) -> FindingEvidence:
        return EvidenceManager.build(
            finding_id=finding_id, evidence_type="report", evidence_source=report_name,
            evidence_version=report_version, lineage_id=lineage_id)

    @staticmethod
    def from_review_action(*, finding_id: str, review_id: str, action: str,
                           lineage_id: Optional[str] = None) -> FindingEvidence:
        return EvidenceManager.build(
            finding_id=finding_id, evidence_type="review_action", evidence_source=review_id,
            evidence_version=action, lineage_id=lineage_id)



def evidence_spec(evidence_type: str, evidence_source: str, evidence_version: str, *,
                  confidence: Optional[float] = None, source_lineage_id: Optional[str] = None,
                  notes: str = "") -> dict:
    """A readable, validated evidence specification consumed by ``FindingService``.

    ``source_lineage_id`` (optional) is the lineage node of the source artifact
    (e.g. the V1 inference node), used to parent the evidence lineage node so the
    finding chain reaches the inference graph.
    """
    if evidence_type not in VALID_EVIDENCE_TYPES:
        raise EvidenceError(f"evidence_type must be one of {VALID_EVIDENCE_TYPES}")
    if not evidence_source or not evidence_version:
        raise EvidenceError("evidence_source and evidence_version are required")
    return {"evidence_type": evidence_type, "evidence_source": evidence_source,
            "evidence_version": evidence_version, "confidence": confidence,
            "source_lineage_id": source_lineage_id, "notes": notes}
