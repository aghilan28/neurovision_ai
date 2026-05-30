"""EEGFoundationService — the governed orchestration hub for Productization P1.

Turns a **real EEG file** into a governed platform asset through one path:

    load (real bytes) -> validate (structured findings) -> store (checksum +
    fingerprint, by reference) -> extract metadata (normalized, deterministic) ->
    mint identity -> shared-lineage node (parented by the Case node) -> immutable
    audit events -> content-addressed version -> registry sync.

Because the EEG lineage node parents the Case node (which parents the patient node),
``verify_chain`` from an EEG asset spans **Patient → Case → EEG Asset**. The service
shares the platform's single ``ml.lineage.LineageTracker`` and reuses the shared
``ImmutableAuditLog`` — no parallel lineage/audit.

Strictly P1: load / validate / understand / store / track / trace / report. No signal
filtering, artifact removal, feature extraction, inference, or analytics.
"""

from __future__ import annotations

import os
from dataclasses import replace
from typing import Optional

from ml.lineage import LineageTracker  # allowed: backend -> ml

from .version import DETERMINISTIC_EPOCH
from .identity import mint_eeg
from .ingestion import load_eeg
from .validation import EEGValidator
from .metadata import normalize
from .storage import LocalEEGStore
from .registry import EEGRegistry
from .audit import make_eeg_audit_log
from .lineage import make_eeg_lineage
from .models.domain import (
    EEGRecord, EEGSource, EEGRegistryRecord, EEGAssetStatus,
)
from .models.domain import EEGMetadata  # noqa: F401  (re-exported via models)
from .reports import (
    build_eeg_summary_report, build_eeg_validation_report, build_eeg_metadata_report,
    build_eeg_registry_report, build_eeg_audit_report, build_eeg_lineage_report,
)

# version chaining for EEG assets (content-addressed, like other subsystems)
from ml.provenance import hash_obj  # allowed: backend -> ml


class EEGFoundationService:
    """Stateful service: EEG registry, shared lineage tracker, immutable audit log, store."""

    def __init__(self, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[EEGRegistry] = None, store: Optional[LocalEEGStore] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or EEGRegistry()
        self.audit = make_eeg_audit_log()
        self.validator = EEGValidator()
        self.store = store or LocalEEGStore()
        self._reports: dict = {}      # eeg_id -> last validation report (object)

    # --- ingestion (the governed admission path) -----------------------------
    def ingest(self, path: str, *, case=None, case_id: Optional[str] = None,
               patient_id: Optional[str] = None, case_lineage_id: Optional[str] = None,
               created_at: str = DETERMINISTIC_EPOCH) -> EEGRecord:
        """Ingest one real EEG file and return its governed :class:`EEGRecord`."""
        if case is not None:
            case_id = getattr(case, "case_id", case_id)
            patient_id = getattr(case, "patient_id", patient_id)
            case_lineage_id = getattr(case, "lineage_id", case_lineage_id)

        # 1. load real bytes
        raw = load_eeg(path)

        # 2. validate -> structured findings
        report = self.validator.validate(raw)
        self._validation_report = report
        valid = report.valid

        # 3. store (checksum + fingerprint), by reference
        fmt_for_store = raw.fmt if raw.fmt and raw.fmt != "UNKNOWN" else "UNKNOWN"
        storage = self.store.store(path, fmt=fmt_for_store, created_at=created_at)

        # 4. identity (content-addressed from format + fingerprint)
        ident = mint_eeg(fmt_for_store, storage.fingerprint)
        storage = replace(storage, version="", lineage_id=None)

        # 5. metadata (normalized, deterministic) — recording_id = the asset id
        metadata, _channel_set, annotations = normalize(raw, recording_id=ident.id)

        source = EEGSource(
            original_filename=os.path.basename(path), fmt=raw.fmt, subtype=raw.subtype,
            file_size_bytes=storage.file_size_bytes, source_patient_field=raw.patient_field,
            source_recording_field=raw.recording_field)

        status = EEGAssetStatus.VALIDATED if valid else EEGAssetStatus.REJECTED

        # 6. lineage node (parent = Case node) + audit trail
        parents = (case_lineage_id,) if case_lineage_id else ()
        node = self.lineage.record(make_eeg_lineage(
            ident.id, fmt=fmt_for_store, parents=parents, case_id=case_id,
            reason="ingested", created_at=created_at,
            extra={"checksum": storage.checksum_sha256, "valid": valid}))
        self.audit.append("eeg_ingested",
                          {"eeg_id": ident.id, "format": raw.fmt, "checksum": storage.checksum_sha256,
                           "lineage_id": node.lineage_id, "case_id": case_id}, created_at=created_at)
        self.audit.append("eeg_validated",
                          {"eeg_id": ident.id, "valid": valid,
                           "validation_signature": report.signature(),
                           "max_severity": report.max_severity}, created_at=created_at)
        self.audit.append("eeg_stored",
                          {"eeg_id": ident.id, "storage_id": storage.storage_id,
                           "fingerprint": storage.fingerprint,
                           "size": storage.file_size_bytes}, created_at=created_at)
        self.audit.append("eeg_metadata_extracted",
                          {"eeg_id": ident.id, "n_channels": metadata.n_channels,
                           "sampling_frequency": metadata.sampling_frequency,
                           "duration_seconds": metadata.duration_seconds}, created_at=created_at)

        storage = replace(storage, lineage_id=node.lineage_id)
        record = EEGRecord(
            eeg_id=ident.id, fmt=fmt_for_store, source=source, metadata=metadata,
            storage=storage, status=status, valid=valid, validation_summary=report.to_dict(),
            annotations=annotations, case_id=case_id, patient_id=patient_id,
            lineage_id=node.lineage_id, audit_state=self.audit.head, created_at=created_at)
        record = self._finalize(record, reason="ingested", created_at=created_at)
        self._reports[record.eeg_id] = report
        return record

    # --- accessors / validation / reports ------------------------------------
    def validation_report_for(self, eeg_id: str):
        return self._reports.get(eeg_id)

    def reports(self, record: EEGRecord) -> dict:
        return {
            "eeg_summary_report": build_eeg_summary_report(record),
            "eeg_validation_report": build_eeg_validation_report(record),
            "eeg_metadata_report": build_eeg_metadata_report(record),
            "eeg_registry_report": build_eeg_registry_report(self.registry),
            "eeg_audit_report": build_eeg_audit_report(self.audit),
            "eeg_lineage_report": build_eeg_lineage_report(record, self.lineage),
        }

    # --- internals ------------------------------------------------------------
    def _finalize(self, record: EEGRecord, *, reason: str, created_at: str) -> EEGRecord:
        version = hash_obj({"state": record.state_signature(),
                            "previous": record.version_previous()})
        record = replace(record, version=version)
        self.audit.append("eeg_version_changed",
                          {"eeg_id": record.eeg_id, "version": version, "reason": reason},
                          created_at=created_at)
        record = replace(record, audit_state=self.audit.head)
        validation_state = "valid" if record.valid else "invalid"
        self.registry.register(EEGRegistryRecord(
            eeg_id=record.eeg_id, fmt=record.fmt, status=EEGAssetStatus.REGISTERED,
            validation_state=validation_state, storage_state="stored",
            metadata_state="extracted", version=version, case_id=record.case_id,
            patient_id=record.patient_id, lineage_id=record.lineage_id,
            audit_state=record.audit_state, content_signature_value=record.state_signature()))
        self.audit.append("eeg_registered",
                          {"eeg_id": record.eeg_id, "version": version}, created_at=created_at)
        record = replace(record, status=EEGAssetStatus.REGISTERED, audit_state=self.audit.head)
        return record


__all__ = ["EEGFoundationService"]
