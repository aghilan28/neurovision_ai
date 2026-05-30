"""CaseService — the governed orchestration hub for the Clinical Case Foundation.

Ties together identity, lifecycle, registry, audit, and lineage into the use cases
that create and evolve a Case, and that link a Case's Study to a registered V1
inference run (integration with the V1 inference/artifact/lineage systems).

Every mutation is: validated → audited (immutable) → lineage-extended →
version-bumped → registry-synced. Nothing happens outside this governed path.
"""

from __future__ import annotations

import os
from typing import Optional

from ml.provenance import content_id, read_json  # allowed: backend -> ml
from ml.lineage import LineageTracker, LineageRecord

from .version import CLINICAL_CASES_VERSION, CASE_REGISTRY_VERSION, DETERMINISTIC_EPOCH
from .identity import mint_identity
from .models.domain import (
    CaseStatus, PatientIdentity, CaseIdentity, StudyIdentity, CaseMetadata,
    CaseState, CaseVersion, CaseRegistryRecord, Case,
)
from .lifecycle import CaseLifecycle
from .audit import ImmutableAuditLog
from .lineage import make_patient_lineage, make_case_lineage, make_study_lineage
from .registry import CaseRegistry
from .validation import CaseValidator
from .reports import (
    build_case_summary_report, build_case_audit_report, build_case_lineage_report,
    build_case_lifecycle_report, build_case_validation_report,
)

_REVIEW_STATE = {
    CaseStatus.CREATED: "not_started", CaseStatus.INGESTED: "not_started",
    CaseStatus.PROCESSING: "not_started", CaseStatus.READY_FOR_REVIEW: "ready",
    CaseStatus.UNDER_REVIEW: "in_review", CaseStatus.REVIEWED: "reviewed",
    CaseStatus.CLOSED: "closed", CaseStatus.ARCHIVED: "archived",
}


class CaseService:
    """Stateful service holding the registry, a shared lineage tracker, and per-case audit logs."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[CaseRegistry] = None):
        self.registry = registry or CaseRegistry()
        self.lineage = lineage_tracker or LineageTracker()
        self.lifecycle = CaseLifecycle()
        self.validator = CaseValidator()
        self._audit_logs: dict[str, ImmutableAuditLog] = {}

    # --- accessors ------------------------------------------------------------
    def audit_log_for(self, case_id: str) -> ImmutableAuditLog:
        return self._audit_logs[case_id]

    # --- create ---------------------------------------------------------------
    def create_case(self, *, patient_key: str, case_key: str,
                    metadata: Optional[CaseMetadata] = None, owner: str = "clinical-ops",
                    created_at: str = DETERMINISTIC_EPOCH) -> Case:
        patient = mint_identity("patient", {"patient_key": patient_key})
        case = mint_identity("case", {"patient_id": patient.id, "case_key": case_key})

        # lineage: patient node -> case node
        patient_node = self.lineage.record(make_patient_lineage(patient.id, created_at=created_at))
        case_node = self.lineage.record(make_case_lineage(
            case.id, patient.id, patient_node.lineage_id, created_at=created_at))

        # audit log (per case), immutable + tamper-evident
        log = ImmutableAuditLog()
        self._audit_logs[case.id] = log
        log.append("case_created", {"case_id": case.id, "patient_id": patient.id,
                                    "case_lineage_id": case_node.lineage_id}, created_at=created_at)

        aggregate = Case(
            identity=CaseIdentity(case.id, patient.id, case.identity_version),
            patient=PatientIdentity(patient.id, patient.identity_version),
            metadata=metadata or CaseMetadata(),
            state=CaseState(CaseStatus.CREATED, entered_at=created_at, transition_count=0),
            version=CaseVersion(version="", previous=None, reason="created", created_at=created_at),
            owner=owner, created_at=created_at, studies=(),
            lineage_id=case_node.lineage_id, audit_head=log.head,
        )
        self._finalize(aggregate, reason="created", created_at=created_at)
        return aggregate

    # --- attach a V1 inference as a Study -------------------------------------
    def attach_inference(self, case: Case, *, inference_id: str, inference_lineage_id: str,
                         dataset_version: Optional[str], artifact_refs: dict,
                         lineage_records: Optional[dict] = None, study_key: Optional[str] = None,
                         created_at: str = DETERMINISTIC_EPOCH) -> Case:
        """Link a registered V1 inference run to this case as a Study (with lineage)."""
        # import the V1 inference lineage nodes into the shared graph (integration)
        if lineage_records:
            self._import_lineage_records(lineage_records)

        study_key = study_key or inference_id
        study = mint_identity("study", {"case_id": case.case_id, "study_key": study_key})
        study_identity = StudyIdentity(
            study_id=study.id, case_id=case.case_id, identity_version=study.identity_version,
            inference_id=inference_id, inference_lineage_id=inference_lineage_id,
            dataset_version=dataset_version, artifact_refs=dict(artifact_refs))

        # lineage: study node (parents: current case head + inference node), then a new case head
        study_node = self.lineage.record(make_study_lineage(
            study.id, case.case_id, case.lineage_id, inference_id=inference_id,
            inference_lineage_id=inference_lineage_id, dataset_version=dataset_version,
            created_at=created_at))
        new_case_node = self.lineage.record(self._advance_case_node(
            case, parents=(case.lineage_id, study_node.lineage_id), created_at=created_at))

        log = self._audit_logs[case.case_id]
        log.append("study_attached", {"study_id": study.id, "inference_id": inference_id,
                                      "inference_lineage_id": inference_lineage_id}, created_at=created_at)
        log.append("lineage_changed", {"lineage_id": new_case_node.lineage_id,
                                       "study_node": study_node.lineage_id}, created_at=created_at)

        case.studies = case.studies + (study_identity,)
        case.lineage_id = new_case_node.lineage_id
        case.audit_head = log.head
        self._finalize(case, reason=f"attach_study:{study.id}", created_at=created_at)
        return case

    def attach_inference_run(self, case: Case, run_dir: str,
                             created_at: str = DETERMINISTIC_EPOCH) -> Case:
        """Attach a V1 offline-inference run directory (reads its registered artifacts)."""
        index = read_json(os.path.join(run_dir, "inference_index.json"))
        manifest_path = os.path.join(run_dir, "_manifest.json")
        manifest = read_json(manifest_path) if os.path.exists(manifest_path) else {"artifacts": {}}
        lineage_path = os.path.join(run_dir, "registries", "lineage.json")
        lineage_records = read_json(lineage_path).get("records") if os.path.exists(lineage_path) else None
        return self.attach_inference(
            case, inference_id=index["inference_id"],
            inference_lineage_id=index["lineage_id"],
            dataset_version=index.get("version_bundle", {}).get("dataset_version"),
            artifact_refs=manifest.get("artifacts", {}), lineage_records=lineage_records,
            created_at=created_at)

    # --- lifecycle transition -------------------------------------------------
    def transition(self, case: Case, target: CaseStatus, reason: str = "",
                   created_at: str = DETERMINISTIC_EPOCH) -> Case:
        record = self.lifecycle.transition(case.state.status, target, reason=reason, created_at=created_at)
        log = self._audit_logs[case.case_id]
        log.append("state_change", record.to_dict(), created_at=created_at)

        new_case_node = self.lineage.record(self._advance_case_node(
            case, parents=(case.lineage_id,), created_at=created_at,
            extra={"transition": record.to_dict()}))

        case.state = CaseState(status=target, entered_at=created_at,
                               transition_count=case.state.transition_count + 1)
        case.lineage_id = new_case_node.lineage_id
        case.audit_head = log.head
        self._finalize(case, reason=f"transition:{record.from_state}->{record.to_state}",
                       created_at=created_at)
        return case

    # --- validation + reports -------------------------------------------------
    def validate(self, case: Case):
        return self.validator.validate(case=case, registry=self.registry,
                                       audit_log=self._audit_logs[case.case_id],
                                       lineage_tracker=self.lineage)

    def reports(self, case: Case) -> dict:
        log = self._audit_logs[case.case_id]
        validation = self.validate(case).to_dict()
        return {
            "case_summary_report": build_case_summary_report(case),
            "case_audit_report": build_case_audit_report(case, log),
            "case_lineage_report": build_case_lineage_report(case, self.lineage),
            "case_lifecycle_report": build_case_lifecycle_report(case, log),
            "case_validation_report": build_case_validation_report(case, validation),
        }

    # --- internals ------------------------------------------------------------
    def _advance_case_node(self, case: Case, *, parents: tuple, created_at: str,
                           extra: Optional[dict] = None) -> LineageRecord:
        from .lineage import make_lineage_record, clinical_version_bundle
        outputs = {"case_id": case.case_id, "status": case.state.status.value}
        if extra:
            outputs.update(extra)
        return make_lineage_record(
            kind="case", versions=clinical_version_bundle(),
            inputs={"case_id": case.case_id, "patient_id": case.patient_id},
            outputs=outputs, parents=parents, created_at=created_at)

    def _finalize(self, case: Case, *, reason: str, created_at: str) -> None:
        """Bump the case version (chained: state + previous), then sync registry."""
        previous = case.version.version or None
        new_version = CaseVersion.compute(case.state_signature(), previous)
        case.version = CaseVersion(version=new_version, previous=previous,
                                   reason=reason, created_at=created_at)
        log = self._audit_logs[case.case_id]
        log.append("version_changed", {"version": new_version, "reason": reason}, created_at=created_at)
        case.audit_head = log.head
        self._sync_registry(case, created_at=created_at)

    def _sync_registry(self, case: Case, *, created_at: str) -> None:
        record = CaseRegistryRecord(
            case_id=case.case_id, patient_id=case.patient_id, study_ids=case.study_ids,
            status=case.state.status, version=case.version.version, owner=case.owner,
            creation_date=case.created_at, review_state=_REVIEW_STATE[case.state.status],
            audit_state=case.audit_head, dependencies=case.dependencies,
            lineage_id=case.lineage_id, case_registry_version=CASE_REGISTRY_VERSION)
        self.registry.register(record)

    def _import_lineage_records(self, records: dict) -> None:
        """Record V1 lineage nodes into the shared tracker so chains verify across V1+V2."""
        for lid, rec in records.items():
            if self.lineage.exists(lid):
                continue
            self.lineage.record(LineageRecord(
                lineage_id=rec["lineage_id"], kind=rec["kind"], versions=rec.get("versions", {}),
                inputs=rec.get("inputs", {}), outputs=rec.get("outputs", {}),
                parents=tuple(rec.get("parents", [])), created_at=rec.get("created_at", DETERMINISTIC_EPOCH),
                lineage_version=rec.get("lineage_version", "lineage@1.0.0")))
