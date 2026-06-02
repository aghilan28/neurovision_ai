"""FindingService — the governed orchestration hub for the Findings & Interpretation Layer.

Ties identity, lifecycle, evidence, interpretation, registry, audit, and lineage
into the use cases that create and evolve a Finding. A finding is created **with
evidence** (never without), links to its Case/Study/Review, and carries separate
Interpretation entities. Every mutation is validated → audited (immutable) →
lineage-extended → version-bumped → registry-synced.

Findings are observations linked to evidence — this service never produces a
diagnosis, recommendation, probability, or decision (forbidden / later phases).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional

from ml.lineage import LineageTracker, make_lineage_record  # allowed: backend -> ml
from .version import CLINICAL_FINDINGS_VERSION, FINDING_REGISTRY_VERSION, DETERMINISTIC_EPOCH
from .identity import mint_finding
from .models.domain import (
    FindingStatus, FindingIdentity, FindingRecord, FindingMetadata,
    FindingVersion, FindingRegistryRecord, Finding,
)
from .lifecycle import FindingLifecycle
from .evidence import EvidenceManager
from .interpretation import InterpretationManager
from .audit import make_finding_audit_log
from .lineage import (
    make_finding_lineage, make_evidence_lineage, make_interpretation_lineage, finding_version_bundle,
)
from .registry import FindingRegistry
from .validation import FindingValidator
from .reports import (
    build_finding_summary_report, build_finding_audit_report, build_finding_lineage_report,
    build_finding_validation_report, build_evidence_report, build_interpretation_report,
)


class FindingService:
    """Stateful service: registry, shared lineage tracker, per-finding audit logs, interpretation store."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[FindingRegistry] = None):
        self.registry = registry or FindingRegistry()
        self.lineage = lineage_tracker or LineageTracker()
        self.lifecycle = FindingLifecycle()
        self.evidence = EvidenceManager()
        self.interpretations = InterpretationManager()
        self.validator = FindingValidator()
        self._audit_logs: dict[str, object] = {}
        self._interpretations: dict[str, object] = {}  # interpretation_id -> FindingInterpretation

    def audit_log_for(self, finding_id: str):
        return self._audit_logs[finding_id]

    def interpretation_store(self) -> dict:
        return dict(self._interpretations)

    # --- create (with mandatory evidence) -------------------------------------
    def create_finding(self, *, review_id: str, case_id: str, study_id: Optional[str],
                        record: FindingRecord, evidence_specs: list,
                        review_lineage_id: Optional[str] = None,
                        inference_lineage_id: Optional[str] = None,
                        metadata: Optional[FindingMetadata] = None, finding_key: Optional[str] = None,
                        owner: str = "clinical-ops", created_at: str = DETERMINISTIC_EPOCH) -> Finding:
        if not evidence_specs:
            raise ValueError("a finding must never be created without evidence (>= 1 required)")
        fid = mint_finding(review_id, finding_key or record.observation)

        log = make_finding_audit_log()
        self._audit_logs[fid.id] = log
        log.append("finding_created", {"finding_id": fid.id, "review_id": review_id,
                                       "case_id": case_id, "study_id": study_id}, created_at=created_at)

        # build evidence + their lineage nodes
        evidence_items = []
        evidence_nodes = []
        for spec in evidence_specs:
            item = EvidenceManager.build(
                finding_id=fid.id, evidence_type=spec["evidence_type"],
                evidence_source=spec["evidence_source"], evidence_version=spec["evidence_version"],
                evidence_confidence=spec.get("confidence"), notes=spec.get("notes", ""))
            node = self.lineage.record(make_evidence_lineage(
                item.evidence_id, fid.id, source_lineage_id=spec.get("source_lineage_id"),
                evidence_type=item.evidence_type, created_at=created_at))
            item = replace(item, lineage_id=node.lineage_id)
            evidence_items.append(item)
            evidence_nodes.append(node.lineage_id)
            log.append("evidence_added", item.to_dict(), created_at=created_at)

        finding_node = self.lineage.record(make_finding_lineage(
            fid.id, review_lineage_id=review_lineage_id,
            evidence_lineage_ids=tuple(evidence_nodes), created_at=created_at))

        finding = Finding(
            identity=FindingIdentity(fid.id, review_id, case_id, study_id, fid.identity_version),
            record=record, metadata=metadata or FindingMetadata(), status=FindingStatus.CREATED,
            version=FindingVersion(version="", previous=None, reason="created", created_at=created_at),
            owner=owner, created_at=created_at, evidence=tuple(evidence_items),
            lineage_id=finding_node.lineage_id, audit_head=log.head,
            review_lineage_id=review_lineage_id, inference_lineage_id=inference_lineage_id)
        self._finalize(finding, reason="created", created_at=created_at)
        return finding

    # --- evidence -------------------------------------------------------------
    def add_evidence(self, finding: Finding, spec: dict, created_at: str = DETERMINISTIC_EPOCH) -> Finding:
        item = EvidenceManager.build(
            finding_id=finding.finding_id, evidence_type=spec["evidence_type"],
            evidence_source=spec["evidence_source"], evidence_version=spec["evidence_version"],
            evidence_confidence=spec.get("confidence"), notes=spec.get("notes", ""))
        node = self.lineage.record(make_evidence_lineage(
            item.evidence_id, finding.finding_id, source_lineage_id=spec.get("source_lineage_id"),
            evidence_type=item.evidence_type, created_at=created_at))
        item = replace(item, lineage_id=node.lineage_id)
        log = self._audit_logs[finding.finding_id]
        log.append("evidence_added", item.to_dict(), created_at=created_at)
        finding.evidence = finding.evidence + (item,)
        self._advance_finding(finding, parents_extra=(node.lineage_id,),
                              reason=f"evidence:{item.evidence_id}", created_at=created_at)
        self._finalize(finding, reason=f"add_evidence:{item.evidence_id}", created_at=created_at)
        return finding

    # --- interpretation (separate entity) -------------------------------------
    def add_interpretation(self, finding: Finding, *, text: str, interpretation_type: str = "descriptive",
                           supporting_evidence: tuple = (), confidence_level: Optional[str] = None,
                           review_references: tuple = (), concept_refs: tuple = (),
                           key: Optional[str] = None, created_at: str = DETERMINISTIC_EPOCH):
        bad = set(supporting_evidence) - set(finding.evidence_ids)
        if bad:
            raise ValueError(f"interpretation cites evidence not on this finding: {sorted(bad)}")
        interp = self.interpretations.new(
            finding_id=finding.finding_id, text=text, interpretation_type=interpretation_type, key=key,
            supporting_evidence=supporting_evidence, confidence_level=confidence_level,
            review_references=review_references, concept_refs=concept_refs)
        node = self.lineage.record(make_interpretation_lineage(
            interp.interpretation_id, finding.finding_id, finding_lineage_id=finding.lineage_id,
            created_at=created_at))
        interp = replace(interp, lineage_id=node.lineage_id)
        self._interpretations[interp.interpretation_id] = interp
        log = self._audit_logs[finding.finding_id]
        log.append("interpretation_added", interp.to_dict(), created_at=created_at)
        finding.interpretation_ids = finding.interpretation_ids + (interp.interpretation_id,)
        self._advance_finding(finding, parents_extra=(node.lineage_id,),
                              reason=f"interpretation:{interp.interpretation_id}", created_at=created_at)
        self._finalize(finding, reason=f"add_interpretation:{interp.interpretation_id}", created_at=created_at)
        return finding, interp

    def set_interpretation_status(self, finding: Finding, interpretation_id: str, status: str,
                                  created_at: str = DETERMINISTIC_EPOCH):
        interp = self._interpretations[interpretation_id]
        interp = self.interpretations.set_status(interp, status)
        self._interpretations[interpretation_id] = interp
        log = self._audit_logs[finding.finding_id]
        log.append("interpretation_changed", {"interpretation_id": interpretation_id, "status": status},
                   created_at=created_at)
        self._finalize(finding, reason=f"interpretation_status:{interpretation_id}:{status}",
                       created_at=created_at)
        return finding, interp

    # --- lifecycle convenience ------------------------------------------------
    def to_draft(self, f, created_at=DETERMINISTIC_EPOCH):
        return self.transition(f, FindingStatus.DRAFT, "draft", created_at)

    def submit_for_review(self, f, created_at=DETERMINISTIC_EPOCH):
        return self.transition(f, FindingStatus.UNDER_REVIEW, "submit", created_at)

    def confirm(self, f, created_at=DETERMINISTIC_EPOCH):
        return self.transition(f, FindingStatus.CONFIRMED, "confirm", created_at)

    def revise(self, f, reason="revise", created_at=DETERMINISTIC_EPOCH):
        return self.transition(f, FindingStatus.REVISED, reason, created_at)

    def supersede(self, f, reason="supersede", created_at=DETERMINISTIC_EPOCH):
        return self.transition(f, FindingStatus.SUPERSEDED, reason, created_at)

    def close(self, f, created_at=DETERMINISTIC_EPOCH):
        return self.transition(f, FindingStatus.CLOSED, "close", created_at)

    def archive(self, f, created_at=DETERMINISTIC_EPOCH):
        return self.transition(f, FindingStatus.ARCHIVED, "archive", created_at)

    def transition(self, finding: Finding, target: FindingStatus, reason: str = "",
                   created_at: str = DETERMINISTIC_EPOCH) -> Finding:
        record = self.lifecycle.transition(finding.status, target, reason=reason, created_at=created_at)
        log = self._audit_logs[finding.finding_id]
        log.append("state_change", record.to_dict(), created_at=created_at)
        finding.status = target
        finding.transition_count += 1
        self._advance_finding(finding, parents_extra=(), reason=f"transition:{target.value}",
                              created_at=created_at, extra_outputs={"transition": record.to_dict()})
        self._finalize(finding, reason=f"transition:{target.value}", created_at=created_at)
        return finding

    # --- validation + reports -------------------------------------------------
    def validate(self, finding: Finding):
        return self.validator.validate(finding=finding, registry=self.registry,
                                       audit_log=self._audit_logs[finding.finding_id],
                                       lineage_tracker=self.lineage,
                                       interpretations=self._interpretations)

    def reports(self, finding: Finding) -> dict:
        log = self._audit_logs[finding.finding_id]
        validation = self.validate(finding).to_dict()
        return {
            "finding_summary_report": build_finding_summary_report(finding),
            "finding_audit_report": build_finding_audit_report(finding, log),
            "finding_lineage_report": build_finding_lineage_report(finding, self.lineage),
            "finding_validation_report": build_finding_validation_report(finding, validation),
            "evidence_report": build_evidence_report(finding),
            "interpretation_report": build_interpretation_report(finding, self._interpretations),
        }

    # --- internals ------------------------------------------------------------
    def _advance_finding(self, finding: Finding, *, parents_extra: tuple, reason: str,
                         created_at: str, extra_outputs: Optional[dict] = None) -> None:
        outputs = {"finding_id": finding.finding_id, "status": finding.status.value}
        if extra_outputs:
            outputs.update(extra_outputs)
        node = self.lineage.record(make_lineage_record(
            kind="finding", versions=finding_version_bundle(),
            inputs={"finding_id": finding.finding_id, "review_id": finding.review_id},
            outputs=outputs, parents=(finding.lineage_id,) + tuple(parents_extra), created_at=created_at))
        finding.lineage_id = node.lineage_id

    def _finalize(self, finding: Finding, *, reason: str, created_at: str) -> None:
        previous = finding.version.version or None
        finding.version = FindingVersion(version=FindingVersion.compute(finding.state_signature(), previous),
                                         previous=previous, reason=reason, created_at=created_at)
        log = self._audit_logs[finding.finding_id]
        log.append("version_changed", {"version": finding.version.version, "reason": reason},
                   created_at=created_at)
        finding.audit_head = log.head
        self._sync_registry(finding)

    def _sync_registry(self, finding: Finding) -> None:
        self.registry.register(FindingRegistryRecord(
            finding_id=finding.finding_id, case_id=finding.case_id, study_id=finding.study_id,
            review_id=finding.review_id, status=finding.status, version=finding.version.version,
            owner=finding.owner, evidence_ids=finding.evidence_ids,
            interpretation_ids=finding.interpretation_ids, lineage_id=finding.lineage_id,
            audit_state=finding.audit_head, finding_registry_version=FINDING_REGISTRY_VERSION))
