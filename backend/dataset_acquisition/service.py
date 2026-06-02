"""``RealDatasetService`` — the Real Dataset Platform hub (Track 1).

Orchestrates the governed real-dataset lifecycle over the **shared** platform lineage
tracker + immutable audit log:

    acquire -> track availability -> connect (read ACTUAL files) -> validate structure ->
    verify labels -> build inventory -> lineage + registry + audit -> score training readiness

It reuses the ``eeg_foundation`` real-file reader, the shared ``ml.lineage`` tracker, the
shared ``ImmutableAuditLog``, ``ml.validation`` and ``ml.provenance`` — **no parallel
systems**. It acquires/validates/registers/verifies/prepares datasets for training; it
trains no models and modifies no other subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ml.lineage import LineageTracker
from ml.provenance import hash_obj

from . import reports as _reports
from .acquisition import acquire as _acquire
from .audit import ImmutableAuditLog, make_acquisition_audit_log
from .connectors import connector_for
from .identity import mint_identity
from .inventory import InventoryBuilder
from .labels import LabelVerifier
from .lineage import (
    make_dataset_lineage, make_label_lineage, make_patient_lineage, make_recording_lineage,
    make_registry_lineage, make_source_lineage,
)
from .models.domain import (
    AcquisitionRecord, AvailabilityState, DatasetSource, EntityKind, RealDatasetRecord,
    AcquisitionRegistryRecord, TrainingReadinessClass,
)
from .readiness import TrainingReadinessEngine
from .registry import RealDatasetRegistry
from .sources import all_specs, spec_for
from .storage import DatasetAvailabilityTracker, DatasetStorageManager
from .validation import StructureValidator
from .version import DETERMINISTIC_EPOCH


class RealDatasetError(RuntimeError):
    """Raised on hub misuse."""


@dataclass(frozen=True)
class RealDatasetOutcome:
    accepted: bool
    source: DatasetSource
    dataset_record: RealDatasetRecord
    acquisition: AcquisitionRecord
    availability: object
    connector_result: object
    validation: object
    label_verification: object
    inventory: object
    readiness: object
    lineage_id: Optional[str] = None
    registry_lineage_id: Optional[str] = None
    audit_head: Optional[str] = None

    @property
    def dataset_id(self) -> str:
        return self.dataset_record.dataset_id

    @property
    def ready_for_training(self) -> bool:
        return self.readiness.classification == TrainingReadinessClass.READY_FOR_TRAINING

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted, "source": self.source.value,
            "dataset": self.dataset_record.to_dict(),
            "acquisition": self.acquisition.to_dict(),
            "availability": self.availability.to_dict(),
            "validation": self.validation.to_dict(),
            "label_verification": self.label_verification.to_dict(),
            "inventory": self.inventory.to_dict(),
            "readiness": self.readiness.to_dict(),
            "lineage_id": self.lineage_id, "registry_lineage_id": self.registry_lineage_id,
            "audit_head": self.audit_head,
            "ready_for_training": self.ready_for_training,
        }


class RealDatasetService:
    def __init__(self, *, data_root: Optional[str] = None,
                 lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[RealDatasetRegistry] = None) -> None:
        self.storage = DatasetStorageManager(data_root)
        self.tracker = DatasetAvailabilityTracker(self.storage)
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or RealDatasetRegistry()
        self.validator = StructureValidator()
        self.label_verifier = LabelVerifier()
        self.inventory_builder = InventoryBuilder()
        self.readiness_engine = TrainingReadinessEngine()
        self._audit_logs: dict[str, ImmutableAuditLog] = {}
        self._outcomes: dict[str, RealDatasetOutcome] = {}

    # --- T1-A acquisition ----------------------------------------------------
    def acquire(self, source: DatasetSource, *, allow_download: bool = True,
                timeout: float = 60.0) -> AcquisitionRecord:
        return _acquire(spec_for(source), self.storage, allow_download=allow_download,
                        timeout=timeout)

    def acquisition_plan(self) -> list:
        """Acquisition plan/report for every mandatory corpus (no downloads)."""
        return [_acquire(spec, self.storage, allow_download=False) for spec in all_specs()]

    def audit_log_for(self, dataset_id: str) -> ImmutableAuditLog:
        return self._audit_logs[dataset_id]

    # --- full integration (T1-B..H) ------------------------------------------
    def integrate(self, source: DatasetSource, *, allow_download: bool = False,
                  timeout: float = 60.0,
                  created_at: str = DETERMINISTIC_EPOCH) -> RealDatasetOutcome:
        spec = spec_for(source)

        # T1-A/B: acquire (idempotent; reuses present files) + track local availability
        acquisition = _acquire(spec, self.storage, allow_download=allow_download, timeout=timeout)
        availability = self.tracker.track(source, expected_files=spec.sample_files)

        # T1-C: connect to the ACTUAL files
        result = connector_for(source, self.storage).connect()

        # T1-D: structure validation
        validation = self.validator.validate(result, availability)
        # T1-E: label verification
        label_verification = self.label_verifier.verify(result)
        # T1-F: inventory
        inventory = self.inventory_builder.build(result)

        # content fingerprint over REAL file checksums + labels (deterministic)
        content_fingerprint = hash_obj({
            "source": source.value,
            "recordings": sorted((r.relative_path, r.checksum_sha256) for r in result.recordings),
            "labels": sorted((label.recording_id, label.value.value) for label in result.labels),
        })
        source_id = mint_identity("dataset_source", {"source": source.value}).id
        dataset_id = mint_identity(
            "real_dataset", {"source": source.value,
                             "content_fingerprint": content_fingerprint}).id

        # T1-H: lineage chain Source -> Dataset -> Patient -> Recording -> Label -> Registry
        source_node = self.lineage.record(
            make_source_lineage(source_id, source=source.value, created_at=created_at))
        dataset_node = self.lineage.record(make_dataset_lineage(
            dataset_id, source_id, source_node.lineage_id,
            content_fingerprint=content_fingerprint, created_at=created_at))

        patient_node_by_key: dict[str, str] = {}
        patient_id_by_key: dict[str, str] = {}
        for patient in result.patients:
            node = self.lineage.record(make_patient_lineage(
                patient.patient_id, dataset_id, dataset_node.lineage_id,
                patient_key=patient.patient_key, created_at=created_at))
            patient_node_by_key[patient.patient_key] = node.lineage_id
            patient_id_by_key[patient.patient_key] = patient.patient_id

        recording_node_by_id: dict[str, str] = {}
        for rec in result.recordings:
            parent = patient_node_by_key.get(rec.patient_id, dataset_node.lineage_id)
            node = self.lineage.record(make_recording_lineage(
                rec.recording_id, rec.patient_id, parent,
                relative_path=rec.relative_path, checksum=rec.checksum_sha256,
                created_at=created_at))
            recording_node_by_id[rec.recording_id] = node.lineage_id

        label_nodes: list[str] = []
        for label in result.labels:
            parent = recording_node_by_id.get(label.recording_id, dataset_node.lineage_id)
            node = self.lineage.record(make_label_lineage(
                label.label_id, label.recording_id, parent,
                scheme=label.scheme.value, value=label.value.value, created_at=created_at))
            label_nodes.append(node.lineage_id)

        registry_parents = (tuple(label_nodes) or tuple(recording_node_by_id.values())
                            or (dataset_node.lineage_id,))
        registry_node = self.lineage.record(make_registry_lineage(
            dataset_id, registry_parents, n_recordings=len(result.recordings),
            n_labels=len(result.labels), created_at=created_at))
        traceable = self.lineage.verify_chain(registry_node.lineage_id)

        # metadata completeness fraction (real, parsed recordings)
        n_rec = len(result.recordings)
        n_complete = sum(1 for r in result.recordings
                         if r.parse_ok and r.sampling_frequency > 0 and r.n_channels > 0
                         and r.n_samples > 0 and r.duration_seconds > 0)
        metadata_fraction = (n_complete / n_rec) if n_rec else 0.0

        # T1-G: readiness
        readiness = self.readiness_engine.assess(
            availability=availability, validation=validation,
            label_verification=label_verification, inventory=inventory,
            metadata_fraction=metadata_fraction, registered=True, traceable=traceable)

        # T1-H: audit (shared ImmutableAuditLog)
        log = make_acquisition_audit_log()
        self._audit_logs[dataset_id] = log
        log.append("dataset_acquired", {"source": source.value, "n_items": len(acquisition.items),
                                        "n_acquired": acquisition.n_acquired}, created_at=created_at)
        log.append("availability_tracked", {"state": availability.state.value,
                                            "n_files": availability.n_files,
                                            "n_verified": availability.n_verified},
                   created_at=created_at)
        log.append("dataset_connected", {"n_recordings": len(result.recordings),
                                        "n_patients": len(result.patients),
                                        "n_discovered": len(result.discovered_files)},
                   created_at=created_at)
        log.append("labels_extracted", {"scheme": result.label_scheme.value,
                                        "n_labels": len(result.labels)}, created_at=created_at)
        log.append("structure_validated", {"validation_id": validation.validation_id,
                                           "ok": validation.ok}, created_at=created_at)
        log.append("labels_verified", {"verification_id": label_verification.verification_id,
                                       "coverage": label_verification.coverage,
                                       "n_classes": label_verification.n_classes},
                   created_at=created_at)
        log.append("inventory_built", {"inventory_id": inventory.inventory_id,
                                       "n_recordings": inventory.n_recordings},
                   created_at=created_at)
        log.append("readiness_scored", {"readiness_id": readiness.readiness_id,
                                        "classification": readiness.classification.value,
                                        "score": readiness.score}, created_at=created_at)
        log.append("dataset_registered", {"dataset_id": dataset_id,
                                          "content_fingerprint": content_fingerprint},
                   created_at=created_at)

        availability_state = (AvailabilityState.READY
                              if readiness.classification == TrainingReadinessClass.READY_FOR_TRAINING
                              else availability.state)

        record = RealDatasetRecord(
            dataset_id=dataset_id, source=source, name=spec.display_name,
            local_root=availability.local_root, content_fingerprint=content_fingerprint,
            n_patients=len(result.patients), n_recordings=len(result.recordings),
            n_labels=len(result.labels), availability_state=availability_state,
            validation_id=validation.validation_id,
            label_verification_id=label_verification.verification_id,
            inventory_id=inventory.inventory_id, readiness_id=readiness.readiness_id,
            source_id=source_id, acquisition_signature=acquisition.spec_signature,
            created_at=created_at, lineage_id=dataset_node.lineage_id,
            registry_lineage_id=registry_node.lineage_id, audit_head=log.head)

        # T1-H: registry (no orphans) — every entity references audit head + lineage node
        self._register_entities(record, source_node.lineage_id, dataset_node.lineage_id,
                                patient_node_by_key, patient_id_by_key, recording_node_by_id,
                                result, label_nodes, registry_node.lineage_id, log.head,
                                created_at)

        outcome = RealDatasetOutcome(
            accepted=True, source=source, dataset_record=record, acquisition=acquisition,
            availability=availability, connector_result=result, validation=validation,
            label_verification=label_verification, inventory=inventory, readiness=readiness,
            lineage_id=dataset_node.lineage_id, registry_lineage_id=registry_node.lineage_id,
            audit_head=log.head)
        self._outcomes[dataset_id] = outcome
        return outcome

    # --- reporting (T1-I) ----------------------------------------------------
    def reports(self, outcome: RealDatasetOutcome) -> dict:
        log = self._audit_logs[outcome.dataset_id]
        return {
            "acquisition_report": _reports.build_acquisition_report([outcome.acquisition]),
            "validation_report": _reports.build_validation_report(outcome.validation),
            "inventory_report": _reports.build_inventory_report(outcome.inventory),
            "label_report": _reports.build_label_report(outcome.label_verification),
            "metadata_report": _reports.build_metadata_report(outcome.connector_result),
            "readiness_report": _reports.build_readiness_report(outcome.readiness),
            "audit_report": _reports.build_audit_report(log, subject=outcome.dataset_id),
            "lineage_report": _reports.build_lineage_report(self.lineage,
                                                            outcome.registry_lineage_id),
            "dataset_summary_report": _reports.build_dataset_summary_report(outcome.dataset_record),
        }

    def acquisition_report(self) -> dict:
        return _reports.build_acquisition_report(self.acquisition_plan())

    # --- internals -----------------------------------------------------------
    def _register_entities(self, record, source_node, dataset_node, patient_node_by_key,
                           patient_id_by_key, recording_node_by_id, result, label_nodes,
                           registry_node, audit_head, created_at) -> None:
        src = record.source.value

        def reg(kind, entity_id, lineage_id, deps=()):
            self.registry.register(AcquisitionRegistryRecord(
                entity_kind=kind, entity_id=entity_id, status=record.availability_state.value,
                version=record.content_fingerprint, owner=record.owner,
                creation_date=created_at, audit_state=audit_head, lineage_id=lineage_id,
                source=src, dependencies=tuple(deps)))

        if not self.registry.exists(record.source_id):
            reg(EntityKind.SOURCE, record.source_id, source_node)
        reg(EntityKind.DATASET, record.dataset_id, dataset_node, (record.source_id,))
        for patient in result.patients:
            reg(EntityKind.PATIENT, patient.patient_id,
                patient_node_by_key[patient.patient_key], (record.dataset_id,))
        for rec in result.recordings:
            parent_patient = patient_id_by_key.get(rec.patient_id, record.dataset_id)
            reg(EntityKind.RECORDING, rec.recording_id, recording_node_by_id[rec.recording_id],
                (parent_patient,))
        label_node_by_id = dict(zip([label.label_id for label in result.labels], label_nodes))
        for label in result.labels:
            reg(EntityKind.LABEL, label.label_id, label_node_by_id[label.label_id],
                (label.recording_id,))
        reg(EntityKind.REGISTRY, f"dataset_registry+{record.dataset_id.split('+')[-1]}",
            registry_node, (record.dataset_id,))


__all__ = ["RealDatasetService", "RealDatasetOutcome", "RealDatasetError"]
