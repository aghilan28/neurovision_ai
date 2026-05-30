"""SignalProcessingService — the governed orchestration hub for Productization P2.

Transforms a raw EEG asset (produced by Productization P1) into a tracked, traceable
*processed (clean) EEG asset*, without ever touching the immutable raw bytes. For a
raw asset the flow is:

    load raw signal (read-only) -> assess quality (before) -> detect artifacts ->
    filter + remove artifacts (deterministic pipeline) -> assess quality (after) ->
    mint identity -> store the clean signal -> record lineage (parented on the raw
    EEG node) -> append immutable audit events -> bump version -> sync registry

Every step is audited; nothing is registered outside this governed path. The service
shares the platform's single ``ml.lineage.LineageTracker`` (so a processed asset's
chain reaches Patient -> Case -> EEG -> Processed) and the shared ``ImmutableAuditLog``
(no parallel audit/lineage systems). It reads the raw bytes from the P1 store but
writes only to a *separate* processed-signal store.

Boundary: imports ``ml`` + ``backend.eeg_foundation`` types + the shared audit
primitive (intra-backend). Never imports ``frontend``. Performs signal processing
only — no feature extraction, modelling, inference, or classification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


from ml.lineage import LineageTracker
from ml.provenance import content_id, hash_obj

from backend.eeg_foundation.storage import LocalEEGStore

from .version import SIGNAL_PROCESSING_VERSION, DETERMINISTIC_EPOCH
from .identity import mint_identity, validate_identity
from .models.domain import (
    ArtifactHistory, ProcessedAssetStatus, ProcessedEEGMetadata,
    ProcessedEEGRecord, ProcessingHistory, QualityHistory, SignalIdentity, SignalKind,
    SignalProcessingRecord, SignalRecord, SignalRegistryRecord, SignalVersion,
)
from .quality import SignalQualityEngine
from .artifacts import ArtifactDetectionEngine
from .preprocessing import (
    ProcessingPipeline, load_raw_signal, RawSignalLoadError, signal_fingerprint, array_fingerprint,
)
from .storage import ProcessedSignalStore
from .registry import SignalRegistry
from .audit import make_signal_audit_log, ImmutableAuditLog
from .lineage import make_signal_lineage
from .validation import SignalIntegrityValidator
from .reports import (
    build_quality_report, build_artifact_report, build_filtering_report,
    build_processing_report, build_audit_report, build_lineage_report, build_registry_report,
)


class SignalProcessingError(RuntimeError):
    """Raised on programmer misuse of the service (not for unusable raw signals)."""


@dataclass(frozen=True)
class ProcessingOutcome:
    """The result of attempting to process one raw EEG asset."""

    accepted: bool
    reason: str
    asset: Optional[ProcessedEEGRecord] = None
    n_artifacts: int = 0

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted, "reason": self.reason,
            "processed_id": self.asset.processed_id if self.asset else None,
            "n_artifacts": self.n_artifacts,
            "asset": self.asset.to_dict() if self.asset else None,
        }


class SignalProcessingService:
    """Stateful service: the raw store (read-only), the processed store, a shared
    lineage tracker, the registry, and per-asset immutable audit logs."""

    def __init__(self, raw_store: LocalEEGStore, processed_store: ProcessedSignalStore, *,
                 lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[SignalRegistry] = None):
        self.raw_store = raw_store
        self.processed_store = processed_store
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or SignalRegistry()
        self.quality_engine = SignalQualityEngine()
        self.detection_engine = ArtifactDetectionEngine()
        self.pipeline = ProcessingPipeline()
        self.integrity_validator = SignalIntegrityValidator()
        self._audit_logs: dict[str, ImmutableAuditLog] = {}
        self._raw_records: dict[str, object] = {}

    # --- accessors ------------------------------------------------------------
    def audit_log_for(self, processed_id: str) -> ImmutableAuditLog:
        return self._audit_logs[processed_id]

    # --- the single use case --------------------------------------------------
    def process(self, eeg_record, *, owner: str = "signal-ops", powerline_hz: float = 60.0,
                band: tuple[float, float] = (0.5, 40.0),
                created_at: str = DETERMINISTIC_EPOCH) -> ProcessingOutcome:
        """Process a raw P1 EEG asset into a clean, tracked processed-EEG asset."""
        eeg_asset_id = eeg_record.asset_id
        case_id, patient_id = eeg_record.case_id, eeg_record.patient_id
        if not validate_identity(eeg_asset_id, "eeg")[0]:
            raise SignalProcessingError(f"invalid eeg_asset_id {eeg_asset_id!r}")
        if not (eeg_record.lineage_id and self.lineage.exists(eeg_record.lineage_id)):
            raise SignalProcessingError(
                "raw EEG lineage node not present in the shared tracker; process with a "
                "shared LineageTracker (Patient -> Case -> EEG -> Processed)")

        # --- load the immutable raw signal (read-only) ------------------------
        try:
            raw_data, sfreq, ch_names = load_raw_signal(
                self.raw_store.abs_path(eeg_record.storage), eeg_record.eeg_format.family)
        except RawSignalLoadError as exc:
            return ProcessingOutcome(accepted=False, reason=f"unreadable_raw: {exc}")

        # --- quality (before) + artifact detection ----------------------------
        quality_before = self.quality_engine.assess(
            raw_data, sfreq, ch_names, eeg_asset_id=eeg_asset_id, signal_kind=SignalKind.RAW)
        artifacts = self.detection_engine.detect_all(raw_data, sfreq, ch_names)

        # --- deterministic cleaning pipeline ----------------------------------
        processed_data, steps, filter_configs, removal_methods, addressed = self.pipeline.run(
            raw_data, sfreq, ch_names, artifacts, powerline_hz=powerline_hz, band=band)
        quality_after = self.quality_engine.assess(
            processed_data, sfreq, ch_names, eeg_asset_id=eeg_asset_id, signal_kind=SignalKind.PROCESSED)

        raw_in_fp = array_fingerprint(raw_data)
        out_fp = array_fingerprint(processed_data)

        # --- mint a content-addressed identity --------------------------------
        processing_key = hash_obj({
            "raw": raw_in_fp, "output": out_fp,
            "steps": [s.to_dict() for s in steps],
            "removal": [m.value for m in removal_methods]})
        identity = mint_identity("signal", {"eeg_asset_id": eeg_asset_id, "processing_key": processing_key})
        processed_id = identity.id

        # --- per-asset immutable audit log ------------------------------------
        log = make_signal_audit_log()
        self._audit_logs[processed_id] = log
        self._raw_records[processed_id] = eeg_record
        log.append("signal_loaded", {
            "processed_id": processed_id, "eeg_asset_id": eeg_asset_id, "case_id": case_id,
            "patient_id": patient_id, "n_channels": int(raw_data.shape[0]),
            "sampling_frequency": round(sfreq, 6), "n_samples": int(raw_data.shape[1]),
            "raw_fingerprint": raw_in_fp}, created_at=created_at)
        log.append("quality_assessed_raw", {
            "quality_id": quality_before.quality_id, "grade": quality_before.grade.value,
            "score": round(quality_before.recording_quality_score, 6),
            "quality_signature": quality_before.signature()}, created_at=created_at)
        log.append("artifacts_detected", {
            "n_artifacts": len(artifacts),
            "types": sorted({a.artifact_type.value for a in artifacts})}, created_at=created_at)

        # --- processing record ------------------------------------------------
        processing = SignalProcessingRecord(
            processing_id=content_id("processing", {
                "eeg_asset_id": eeg_asset_id, "input_fingerprint": raw_in_fp,
                "output_fingerprint": out_fp, "steps": [s.to_dict() for s in steps]}),
            eeg_asset_id=eeg_asset_id, filter_configs=filter_configs,
            removal_methods=removal_methods, steps=steps,
            input_fingerprint=raw_in_fp, output_fingerprint=out_fp)
        log.append("signal_processed", {
            "processing_id": processing.processing_id, "n_steps": len(steps),
            "filters": [c.filter_type.value for c in filter_configs],
            "removal_methods": [m.value for m in removal_methods],
            "processing_signature": processing.signature()}, created_at=created_at)
        log.append("quality_assessed_processed", {
            "quality_id": quality_after.quality_id, "grade": quality_after.grade.value,
            "score": round(quality_after.recording_quality_score, 6),
            "quality_signature": quality_after.signature()}, created_at=created_at)

        # --- store the clean signal (separate store; raw untouched) -----------
        storage = self.processed_store.put(processed_data, sfreq=sfreq, channel_labels=ch_names,
                                           created_at=created_at)
        log.append("signal_stored", {
            "storage_id": storage.storage_id, "processed_file_reference": storage.processed_file_reference,
            "checksum_sha256": storage.checksum_sha256,
            "content_fingerprint": storage.content_fingerprint}, created_at=created_at)

        # --- lineage: processed node parented on the raw EEG node -------------
        node = self.lineage.record(make_signal_lineage(
            processed_id, eeg_asset_id, eeg_record.lineage_id, quality_id=quality_after.quality_id,
            processing_id=processing.processing_id, processed_fingerprint=out_fp, created_at=created_at))
        log.append("signal_lineage_recorded", {
            "lineage_id": node.lineage_id, "parents": list(node.parents)}, created_at=created_at)

        # --- assemble the aggregate -------------------------------------------
        raw_signal = SignalRecord(
            signal_kind=SignalKind.RAW, n_channels=int(raw_data.shape[0]),
            sampling_frequency=sfreq, n_samples=int(raw_data.shape[1]),
            channel_labels=tuple(ch_names),
            content_fingerprint=signal_fingerprint(raw_data, sfreq, tuple(ch_names)))
        processed_signal = SignalRecord(
            signal_kind=SignalKind.PROCESSED, n_channels=int(processed_data.shape[0]),
            sampling_frequency=sfreq, n_samples=int(processed_data.shape[1]),
            channel_labels=tuple(ch_names),
            content_fingerprint=signal_fingerprint(processed_data, sfreq, tuple(ch_names)))
        applied_filters = tuple(dict.fromkeys(c.filter_type.value for c in filter_configs))
        metadata = ProcessedEEGMetadata(
            n_channels=int(processed_data.shape[0]), sampling_frequency=sfreq,
            n_samples=int(processed_data.shape[1]),
            duration_seconds=processed_data.shape[1] / sfreq if sfreq > 0 else 0.0,
            channel_labels=tuple(ch_names), applied_filters=applied_filters,
            removal_methods=tuple(m.value for m in removal_methods),
            n_artifacts_detected=len(artifacts), n_artifacts_addressed=len(addressed),
            quality_grade=quality_after.grade)

        asset = ProcessedEEGRecord(
            identity=SignalIdentity(processed_id=processed_id, eeg_asset_id=eeg_asset_id,
                                    identity_version=identity.identity_version),
            eeg_asset_id=eeg_asset_id, case_id=case_id, patient_id=patient_id,
            raw_signal=raw_signal, processed_signal=processed_signal, quality=quality_after,
            artifacts=artifacts, processing=processing,
            processing_history=ProcessingHistory(steps=steps),
            artifact_history=ArtifactHistory(artifacts=artifacts, addressed_artifact_ids=addressed),
            quality_history=QualityHistory(before=quality_before, after=quality_after),
            storage=storage, metadata=metadata, status=ProcessedAssetStatus.PROCESSED,
            version=SignalVersion(version="", previous=None, reason="processed", created_at=created_at),
            owner=owner, created_at=created_at, lineage_id=node.lineage_id, audit_head=log.head)

        self._finalize(asset, reason="processed", created_at=created_at)
        return ProcessingOutcome(accepted=True, reason="processed", asset=asset, n_artifacts=len(artifacts))

    # --- validation + reports -------------------------------------------------
    def integrity(self, asset: ProcessedEEGRecord):
        raw_record = self._raw_records.get(asset.processed_id)
        return self.integrity_validator.validate(
            asset=asset, registry=self.registry, audit_log=self._audit_logs[asset.processed_id],
            lineage_tracker=self.lineage, store=self.processed_store, raw_store=self.raw_store,
            raw_storage_record=getattr(raw_record, "storage", None))

    def reports(self, asset: ProcessedEEGRecord) -> dict:
        log = self._audit_logs[asset.processed_id]
        return {
            "quality_report": build_quality_report(asset),
            "artifact_report": build_artifact_report(asset),
            "filtering_report": build_filtering_report(asset),
            "processing_report": build_processing_report(asset),
            "registry_report": build_registry_report(self.registry),
            "audit_report": build_audit_report(asset, log),
            "lineage_report": build_lineage_report(asset, self.lineage),
        }

    # --- internals ------------------------------------------------------------
    def _finalize(self, asset: ProcessedEEGRecord, *, reason: str, created_at: str) -> None:
        previous = asset.version.version or None
        new_version = SignalVersion.compute(asset.state_signature(), previous)
        asset.version = SignalVersion(version=new_version, previous=previous,
                                      reason=reason, created_at=created_at)
        log = self._audit_logs[asset.processed_id]
        log.append("signal_version_changed", {"version": new_version, "reason": reason},
                   created_at=created_at)
        log.append("signal_registered", {"processed_id": asset.processed_id,
                   "status": asset.status.value}, created_at=created_at)
        asset.audit_head = log.head
        self._sync_registry(asset)

    def _sync_registry(self, asset: ProcessedEEGRecord) -> None:
        self.registry.register(SignalRegistryRecord(
            processed_id=asset.processed_id, eeg_asset_id=asset.eeg_asset_id, case_id=asset.case_id,
            patient_id=asset.patient_id, status=asset.status, quality_grade=asset.quality.grade,
            n_artifacts_detected=len(asset.artifacts),
            n_artifacts_addressed=len(asset.artifact_history.addressed_artifact_ids),
            quality_id=asset.quality.quality_id, processing_id=asset.processing.processing_id,
            storage_state=("stored" if self.processed_store.exists(asset.storage) else "absent"),
            version=asset.version.version, owner=asset.owner, creation_date=asset.created_at,
            audit_state=asset.audit_head or "", lineage_id=asset.lineage_id or "",
            dependencies=(asset.eeg_asset_id,)))

    @property
    def version(self) -> str:
        return SIGNAL_PROCESSING_VERSION
