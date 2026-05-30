"""FeatureEngineeringService — the governed orchestration hub for Productization P3.

Transforms a processed (clean) EEG asset (from Productization P2) into an
**immutable** feature asset, without touching the processed signal. For a processed
asset the flow is:

    load processed signal (read-only) -> run the five feature engines (frequency,
    temporal, connectivity, spectral, topography) -> validate content (incl. a
    determinism re-extraction) -> group features -> mint identity -> record lineage
    (parented on the processed-EEG node) -> append immutable audit events -> bump
    version -> sync registry

Every step is audited; nothing is registered outside this governed path. The service
shares the platform's single ``ml.lineage.LineageTracker`` (so a feature asset's
chain reaches Patient -> Case -> EEG -> Processed -> Feature) and the shared
``ImmutableAuditLog`` (no parallel audit/lineage systems). It reads the processed
bytes from the P2 store but never writes to it. No model training, inference,
classification, predictions, or clinical decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ml.lineage import LineageTracker
from ml.provenance import content_id, hash_obj

from .version import FEATURE_ENGINEERING_VERSION, DETERMINISTIC_EPOCH
from .identity import mint_identity, validate_identity
from .loader import load_processed_signal, ProcessedSignalLoadError
from .models.domain import (
    FeatureAssetStatus, FeatureFamily, FeatureGroupRecord, FeatureIdentity, FeatureMetadata,
    FeatureRecord, FeatureRegistryRecord, FeatureValidationRecord, FeatureVersion, FrequencyBand,
)
from .frequency import FrequencyFeatureEngine
from .temporal import TemporalFeatureEngine
from .connectivity import ConnectivityFeatureEngine
from .spectral import SpectralRepresentationEngine
from .topography import TopographyRepresentationEngine
from .validation import FeatureContentValidator, FeatureIntegrityValidator
from .registry import FeatureRegistry
from .audit import make_feature_audit_log, ImmutableAuditLog
from .lineage import make_feature_lineage
from .reports import (
    build_frequency_report, build_temporal_report, build_connectivity_report,
    build_spectral_report, build_topography_report, build_audit_report,
    build_lineage_report, build_validation_report, build_registry_report,
)

_FAMILY_ORDER = (FeatureFamily.FREQUENCY, FeatureFamily.TEMPORAL, FeatureFamily.CONNECTIVITY,
                 FeatureFamily.SPECTRAL, FeatureFamily.TOPOGRAPHY)


class FeatureEngineeringError(RuntimeError):
    """Raised on programmer misuse of the service (not for unusable processed signals)."""


@dataclass(frozen=True)
class FeatureOutcome:
    """The result of attempting to generate features for one processed EEG asset."""

    accepted: bool
    reason: str
    asset: Optional[FeatureRecord] = None
    n_vectors: int = 0

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted, "reason": self.reason,
            "feature_asset_id": self.asset.feature_asset_id if self.asset else None,
            "n_vectors": self.n_vectors,
            "asset": self.asset.to_dict() if self.asset else None,
        }


class FeatureEngineeringService:
    """Stateful service: the processed store (read-only), a shared lineage tracker,
    the registry, the five engines, and per-asset immutable audit logs."""

    def __init__(self, processed_store, *, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[FeatureRegistry] = None):
        self.processed_store = processed_store
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or FeatureRegistry()
        self.frequency_engine = FrequencyFeatureEngine()
        self.temporal_engine = TemporalFeatureEngine()
        self.connectivity_engine = ConnectivityFeatureEngine()
        self.spectral_engine = SpectralRepresentationEngine()
        self.topography_engine = TopographyRepresentationEngine()
        self.content_validator = FeatureContentValidator()
        self.integrity_validator = FeatureIntegrityValidator()
        self._audit_logs: dict[str, ImmutableAuditLog] = {}

    def audit_log_for(self, feature_asset_id: str) -> ImmutableAuditLog:
        return self._audit_logs[feature_asset_id]

    # --- the single use case --------------------------------------------------
    def generate_features(self, processed_record, *, owner: str = "feature-ops",
                          created_at: str = DETERMINISTIC_EPOCH) -> FeatureOutcome:
        """Generate a feature asset from a processed (clean) EEG asset."""
        processed_id = processed_record.processed_id
        case_id, patient_id, eeg_asset_id = (
            processed_record.case_id, processed_record.patient_id, processed_record.eeg_asset_id)
        if not validate_identity(processed_id, "signal")[0]:
            raise FeatureEngineeringError(f"invalid processed_id {processed_id!r}")
        if not (processed_record.lineage_id and self.lineage.exists(processed_record.lineage_id)):
            raise FeatureEngineeringError(
                "processed lineage node not present in the shared tracker; generate with a "
                "shared LineageTracker (Patient -> Case -> EEG -> Processed -> Feature)")

        # --- load the processed signal (read-only) ----------------------------
        try:
            data, sfreq, ch_names = load_processed_signal(self.processed_store, processed_record)
        except ProcessedSignalLoadError as exc:
            return FeatureOutcome(accepted=False, reason=f"unreadable_processed: {exc}")

        # --- run the five engines (extraction pass 1) -------------------------
        vectors = self._extract(data, sfreq, ch_names)
        # --- determinism: a second extraction must reproduce identical fingerprints
        vectors2 = self._extract(data, sfreq, ch_names)
        fps1 = [v.content_fingerprint for v in vectors]
        fps2 = [v.content_fingerprint for v in vectors2]
        determinism_ok = fps1 == fps2
        det_detail = {"equal": determinism_ok, "combined": hash_obj(fps1)}

        # --- content validation -----------------------------------------------
        expected_families = [f.value for f in _FAMILY_ORDER]
        checks = self.content_validator.content_checks(
            vectors, expected_families=expected_families, n_channels=data.shape[0],
            determinism_ok=determinism_ok, determinism_detail=det_detail)
        content_ok = all(passed for _, passed, _ in checks)
        validation = FeatureValidationRecord(
            validation_id=content_id("feature-validation", {
                "processed_id": processed_id, "checks": [[n, bool(p)] for n, p, _ in checks]}),
            ok=content_ok, checks=tuple(checks))

        # --- group features by family -----------------------------------------
        groups = []
        for fam in _FAMILY_ORDER:
            fam_vectors = tuple(v for v in vectors if v.family == fam)
            if fam_vectors:
                groups.append(FeatureGroupRecord(family=fam, vectors=fam_vectors))
        groups = tuple(groups)

        # --- metadata ----------------------------------------------------------
        config = self._extraction_config(sfreq)
        metadata = FeatureMetadata(
            processed_id=processed_id, eeg_asset_id=eeg_asset_id, n_channels=int(data.shape[0]),
            sampling_frequency=sfreq, n_samples=int(data.shape[1]),
            duration_seconds=(data.shape[1] / sfreq if sfreq > 0 else 0.0),
            channel_labels=tuple(ch_names),
            families_present=tuple(sorted({v.family.value for v in vectors})),
            groups_present=tuple(sorted({v.group.value for v in vectors})),
            n_vectors=len(vectors), n_values_total=sum(v.n_values for v in vectors),
            frequency_bands={b.value: list(b.hz) for b in FrequencyBand},
            extraction_config=config)

        # --- identity (content-addressed from processed id + extraction fingerprint)
        feature_key = hash_obj({"vectors": fps1, "config": config})
        identity_obj = mint_identity("feature", {"processed_id": processed_id,
                                                 "feature_key": feature_key})
        feature_asset_id = identity_obj.id
        identity = FeatureIdentity(feature_asset_id=feature_asset_id, processed_id=processed_id,
                                   identity_version=identity_obj.identity_version)
        status = FeatureAssetStatus.GENERATED if content_ok else FeatureAssetStatus.QUARANTINED
        dependencies = (processed_id,)

        # --- version (over the immutable state) -------------------------------
        state_sig = FeatureRecord.state_signature_of(
            identity=identity, processed_id=processed_id, eeg_asset_id=eeg_asset_id,
            case_id=case_id, patient_id=patient_id, groups=groups, metadata=metadata,
            validation=validation, status=status, dependencies=dependencies)
        version = FeatureVersion(version=FeatureVersion.compute(state_sig, None), previous=None,
                                 reason="generated", created_at=created_at)

        # --- audit + lineage ---------------------------------------------------
        log = make_feature_audit_log()
        self._audit_logs[feature_asset_id] = log
        log.append("features_extracted", {
            "feature_asset_id": feature_asset_id, "processed_id": processed_id,
            "n_vectors": len(vectors), "families": list(metadata.families_present)},
            created_at=created_at)
        log.append("features_validated", {
            "validation_id": validation.validation_id, "ok": validation.ok,
            "validation_signature": validation.signature()}, created_at=created_at)
        node = self.lineage.record(make_feature_lineage(
            feature_asset_id, processed_id, processed_record.lineage_id,
            families=metadata.families_present, n_vectors=len(vectors),
            feature_fingerprint=feature_key, created_at=created_at))
        log.append("feature_lineage_recorded", {
            "lineage_id": node.lineage_id, "parents": list(node.parents)}, created_at=created_at)
        log.append("feature_version_changed", {"version": version.version, "reason": "generated"},
                   created_at=created_at)
        reg_kind = "feature_registered" if status == FeatureAssetStatus.GENERATED else "feature_quarantined"
        log.append(reg_kind, {"feature_asset_id": feature_asset_id, "status": status.value},
                   created_at=created_at)

        # --- assemble the immutable asset -------------------------------------
        asset = FeatureRecord(
            identity=identity, processed_id=processed_id, eeg_asset_id=eeg_asset_id,
            case_id=case_id, patient_id=patient_id, groups=groups, metadata=metadata,
            validation=validation, status=status, version=version, owner=owner,
            created_at=created_at, lineage_id=node.lineage_id, audit_head=log.head,
            dependencies=dependencies)

        self._sync_registry(asset)
        return FeatureOutcome(accepted=True, reason=status.value, asset=asset, n_vectors=len(vectors))

    # --- validation + reports -------------------------------------------------
    def integrity(self, asset: FeatureRecord):
        return self.integrity_validator.validate(
            asset=asset, registry=self.registry,
            audit_log=self._audit_logs[asset.feature_asset_id], lineage_tracker=self.lineage)

    def reports(self, asset: FeatureRecord) -> dict:
        log = self._audit_logs[asset.feature_asset_id]
        return {
            "frequency_report": build_frequency_report(asset),
            "temporal_report": build_temporal_report(asset),
            "connectivity_report": build_connectivity_report(asset),
            "spectral_report": build_spectral_report(asset),
            "topography_report": build_topography_report(asset),
            "registry_report": build_registry_report(self.registry),
            "audit_report": build_audit_report(asset, log),
            "lineage_report": build_lineage_report(asset, self.lineage),
            "validation_report": build_validation_report(asset, self.integrity(asset)),
        }

    # --- internals ------------------------------------------------------------
    def _extract(self, data, sfreq, ch_names) -> tuple:
        vectors = []
        vectors += list(self.frequency_engine.extract(data, sfreq, ch_names))
        vectors += list(self.temporal_engine.extract(data, sfreq, ch_names))
        vectors += list(self.connectivity_engine.extract(data, sfreq, ch_names))
        vectors += list(self.spectral_engine.extract(data, sfreq, ch_names))
        vectors += list(self.topography_engine.extract(data, sfreq, ch_names))
        return tuple(vectors)

    def _extraction_config(self, sfreq: float) -> dict:
        return {
            "sampling_frequency": round(float(sfreq), 6),
            "nperseg_policy": "min(256, n_samples)",
            "frequency_engine": self.frequency_engine.version,
            "temporal_engine": self.temporal_engine.version,
            "connectivity_engine": self.connectivity_engine.version,
            "spectral_engine": self.spectral_engine.version,
            "topography_engine": self.topography_engine.version,
        }

    def _sync_registry(self, asset: FeatureRecord) -> None:
        self.registry.register(FeatureRegistryRecord(
            feature_asset_id=asset.feature_asset_id, processed_id=asset.processed_id,
            eeg_asset_id=asset.eeg_asset_id, case_id=asset.case_id, patient_id=asset.patient_id,
            status=asset.status, families=asset.families, groups=asset.group_names,
            n_vectors=len(asset.vectors), n_values_total=asset.metadata.n_values_total,
            version=asset.version.version, owner=asset.owner, creation_date=asset.created_at,
            audit_state=asset.audit_head or "", lineage_id=asset.lineage_id or "",
            dependencies=asset.dependencies))

    @property
    def version(self) -> str:
        return FEATURE_ENGINEERING_VERSION
