"""EEGFoundationService — the governed orchestration hub for the EEG Foundation.

Ties together ingestion, validation, metadata extraction, storage, identity,
lineage, and audit into the single use case this phase delivers: *a real EEG file
enters the platform and becomes a tracked, traceable NeuroVision EEG asset.*

For every accepted file the flow is:

    load (real parse) -> validate (structured findings) -> extract metadata ->
    store (content-addressed) -> mint identity -> record lineage (parented on the
    case) -> append immutable audit events -> bump version -> sync registry

Every step is audited; nothing is registered outside this governed path. The
service shares the platform's single ``ml.lineage.LineageTracker`` (so an EEG
asset's chain reaches Patient -> Case -> EEG) and the shared ``ImmutableAuditLog``
(no parallel audit/lineage systems).

Boundary: imports ``ml`` (provenance/lineage/validation) and the platform audit
primitive from ``backend.clinical_cases.audit`` (intra-backend reuse). It never
imports ``frontend`` and performs no signal processing, modelling, or inference
(forbidden in this phase).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from ml.lineage import LineageTracker

from .version import EEG_FOUNDATION_VERSION, DETERMINISTIC_EPOCH
from .identity import mint_identity, validate_identity
from .models.domain import (
    EEGAnnotation, EEGAssetStatus, EEGChannel, EEGChannelSet, EEGIdentity,
    EEGRecord, EEGRegistryRecord, EEGSource, EEGValidationResult, EEGVersion, EEGFormat,
)
from .ingestion import load_eeg
from .validation import EEGFileValidator, EEGIntegrityValidator
from .metadata import extract_metadata
from .storage import LocalEEGStore, fingerprint_of_checksum
from .registry import EEGRegistry
from .audit import make_eeg_audit_log, ImmutableAuditLog
from .lineage import make_eeg_lineage
from .reports import (
    build_eeg_summary_report, build_eeg_metadata_report, build_eeg_validation_report,
    build_eeg_audit_report, build_eeg_lineage_report, build_eeg_registry_report,
)


class EEGFoundationError(RuntimeError):
    """Raised on programmer misuse of the service (not for bad input files)."""


@dataclass(frozen=True)
class IngestionOutcome:
    """The result of attempting to ingest one real EEG file.

    ``accepted`` is True when the file became a registered/quarantined asset.
    Unreadable or unsupported files are *rejected* (``asset is None``) but always
    carry their structured ``validation`` findings, so nothing fails silently.
    """

    accepted: bool
    reason: str
    validation: EEGValidationResult
    asset: Optional[EEGRecord] = None
    detected_format: Optional[EEGFormat] = None

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted,
            "reason": self.reason,
            "detected_format": self.detected_format.value if self.detected_format else None,
            "asset_id": self.asset.asset_id if self.asset else None,
            "validation": self.validation.to_dict(),
            "asset": self.asset.to_dict() if self.asset else None,
        }


class EEGFoundationService:
    """Stateful service: the store, a shared lineage tracker, the registry, and
    per-asset immutable audit logs."""

    def __init__(self, store: LocalEEGStore, *, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[EEGRegistry] = None):
        self.store = store
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or EEGRegistry()
        self.file_validator = EEGFileValidator()
        self.integrity_validator = EEGIntegrityValidator()
        self._audit_logs: dict[str, ImmutableAuditLog] = {}

    # --- accessors ------------------------------------------------------------
    def audit_log_for(self, asset_id: str) -> ImmutableAuditLog:
        return self._audit_logs[asset_id]

    # --- the single use case --------------------------------------------------
    def ingest_eeg(self, file_path: str, *, case_id: str, patient_id: str,
                   case_lineage_id: str, owner: str = "eeg-ops",
                   created_at: str = DETERMINISTIC_EPOCH) -> IngestionOutcome:
        """Ingest a real EEG file into the platform under an existing case."""
        # --- preconditions (caller misuse -> raise; bad *files* -> findings) ---
        if not validate_identity(case_id, "case")[0]:
            raise EEGFoundationError(f"invalid case_id {case_id!r}")
        if not validate_identity(patient_id, "patient")[0]:
            raise EEGFoundationError(f"invalid patient_id {patient_id!r}")
        if not self.lineage.exists(case_lineage_id):
            raise EEGFoundationError(
                "case lineage node not present in the shared tracker; create the case "
                "with a shared LineageTracker before ingesting EEG (Patient -> Case -> EEG)")

        # --- load + validate (never raises on bad files) ----------------------
        parsed = load_eeg(file_path)
        vresult = self.file_validator.validate(parsed)

        # --- reject unreadable / unsupported (cannot become an asset) ----------
        if parsed.checksum_sha256 == "" or parsed.detected_format is None:
            reason = vresult.findings[0].code if vresult.findings else "rejected"
            return IngestionOutcome(accepted=False, reason=reason, validation=vresult,
                                    asset=None, detected_format=parsed.detected_format)

        fmt: EEGFormat = parsed.detected_format

        # --- mint a content-addressed identity (eeg_key = file fingerprint) ----
        fingerprint = fingerprint_of_checksum(parsed.checksum_sha256)
        identity = mint_identity("eeg", {"case_id": case_id, "eeg_key": fingerprint})
        asset_id = identity.id

        # --- per-asset immutable audit log -------------------------------------
        log = make_eeg_audit_log()
        self._audit_logs[asset_id] = log
        log.append("eeg_ingested", {
            "asset_id": asset_id, "case_id": case_id, "patient_id": patient_id,
            "detected_format": fmt.value,
            "declared_format": parsed.declared_format.value if parsed.declared_format else None,
            "checksum_sha256": parsed.checksum_sha256, "file_size_bytes": parsed.file_size_bytes,
            "parse_ok": parsed.parse_ok}, created_at=created_at)
        log.append("eeg_validated", {
            "ok": vresult.ok, "counts": vresult.counts(),
            "validation_signature": vresult.signature()}, created_at=created_at)

        # --- metadata (deterministic, stored independently of raw bytes) -------
        metadata = extract_metadata(parsed)
        log.append("eeg_metadata_extracted", {
            "recording_id": metadata.recording_id,
            "metadata_signature": metadata.signature()}, created_at=created_at)

        # --- store the raw file (content-addressed, checksummed) ---------------
        storage = self.store.put(file_path, eeg_format=fmt, created_at=created_at)
        log.append("eeg_stored", {
            "storage_id": storage.storage_id, "raw_file_reference": storage.raw_file_reference,
            "checksum_sha256": storage.checksum_sha256,
            "content_fingerprint": storage.content_fingerprint,
            "file_size_bytes": storage.file_size_bytes}, created_at=created_at)

        # --- lineage: EEG node parented on the case node (shared tracker) ------
        eeg_node = self.lineage.record(make_eeg_lineage(
            asset_id, case_id, case_lineage_id, recording_id=metadata.recording_id,
            eeg_format=fmt.value, checksum_sha256=parsed.checksum_sha256, created_at=created_at))
        log.append("eeg_lineage_recorded", {
            "lineage_id": eeg_node.lineage_id, "parents": list(eeg_node.parents)},
            created_at=created_at)
        storage = replace(storage, lineage_refs=(eeg_node.lineage_id,))

        # --- assemble the aggregate -------------------------------------------
        source = EEGSource(
            original_filename=parsed.original_filename, detected_format=fmt,
            file_size_bytes=parsed.file_size_bytes,
            source_checksum_sha256=parsed.checksum_sha256, declared_format=parsed.declared_format)
        channel_set = EEGChannelSet(channels=tuple(
            EEGChannel(label=c.label, channel_type=c.channel_type, unit=c.unit,
                       sampling_frequency=c.sampling_frequency) for c in parsed.channels))
        annotations = tuple(
            EEGAnnotation(onset_seconds=o, duration_seconds=d, description=desc)
            for (o, d, desc) in parsed.annotations)
        status = EEGAssetStatus.REGISTERED if vresult.ok else EEGAssetStatus.QUARANTINED

        asset = EEGRecord(
            identity=EEGIdentity(asset_id=asset_id, case_id=case_id,
                                 identity_version=identity.identity_version),
            case_id=case_id, patient_id=patient_id, source=source, eeg_format=fmt,
            channel_set=channel_set, annotations=annotations, metadata=metadata,
            storage=storage, validation=vresult, status=status,
            version=EEGVersion(version="", previous=None, reason="ingested", created_at=created_at),
            owner=owner, created_at=created_at, lineage_id=eeg_node.lineage_id, audit_head=log.head)

        self._finalize(asset, reason="ingested", created_at=created_at)
        return IngestionOutcome(
            accepted=True, reason=("registered" if vresult.ok else "quarantined"),
            validation=vresult, asset=asset, detected_format=fmt)

    # --- validation + reports -------------------------------------------------
    def integrity(self, asset: EEGRecord):
        return self.integrity_validator.validate(
            asset=asset, registry=self.registry,
            audit_log=self._audit_logs[asset.asset_id], lineage_tracker=self.lineage,
            store=self.store)

    def reports(self, asset: EEGRecord) -> dict:
        log = self._audit_logs[asset.asset_id]
        return {
            "eeg_summary_report": build_eeg_summary_report(asset),
            "eeg_metadata_report": build_eeg_metadata_report(asset),
            "eeg_validation_report": build_eeg_validation_report(asset),
            "eeg_audit_report": build_eeg_audit_report(asset, log),
            "eeg_lineage_report": build_eeg_lineage_report(asset, self.lineage),
            "eeg_registry_report": build_eeg_registry_report(self.registry),
        }

    # --- internals ------------------------------------------------------------
    def _finalize(self, asset: EEGRecord, *, reason: str, created_at: str) -> None:
        """Bump the asset version (chained), audit it + the registration, sync registry."""
        previous = asset.version.version or None
        new_version = EEGVersion.compute(asset.state_signature(), previous)
        asset.version = EEGVersion(version=new_version, previous=previous,
                                   reason=reason, created_at=created_at)
        log = self._audit_logs[asset.asset_id]
        log.append("eeg_version_changed", {"version": new_version, "reason": reason},
                   created_at=created_at)
        reg_kind = "eeg_registered" if asset.status == EEGAssetStatus.REGISTERED else "eeg_quarantined"
        log.append(reg_kind, {"asset_id": asset.asset_id, "status": asset.status.value},
                   created_at=created_at)
        asset.audit_head = log.head
        self._sync_registry(asset)

    def _sync_registry(self, asset: EEGRecord) -> None:
        record = EEGRegistryRecord(
            asset_id=asset.asset_id, case_id=asset.case_id, patient_id=asset.patient_id,
            eeg_format=asset.eeg_format, status=asset.status,
            validation_state=("ok" if asset.validation.ok else "has_errors"),
            storage_state=("stored" if self.store.exists(asset.storage) else "absent"),
            metadata_state="extracted", version=asset.version.version, owner=asset.owner,
            creation_date=asset.created_at, audit_state=asset.audit_head or "",
            lineage_id=asset.lineage_id or "", dependencies=asset.dependencies)
        self.registry.register(record)

    @property
    def version(self) -> str:
        return EEG_FOUNDATION_VERSION
