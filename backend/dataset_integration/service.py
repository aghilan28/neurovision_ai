"""DatasetIntegrationService — the Real Dataset Integration hub (DRP-1).

Orchestrates the governed external-dataset lifecycle over the **shared** platform lineage
tracker + immutable audit log:

    inventory -> register -> validate -> govern -> score readiness -> lineage -> audit

It reuses the model-foundation connector framework for supported sources (integration, not
duplication), reuses ``ml.lineage`` + the shared ``ImmutableAuditLog`` + ``ml.validation``,
and creates **no** parallel systems. It manages datasets; it trains no models and modifies
no other subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ml.lineage import LineageTracker

from .version import DETERMINISTIC_EPOCH
from .identity import mint_identity
from .models.domain import (
    DatasetIdentity, DatasetRecord, DatasetRegistryRecord, DatasetSourceRecord, DatasetVersion,
    EegDatasetSource, EntityKind, InventoryStatus,
)
from .audit import make_dataset_audit_log, ImmutableAuditLog
from .lineage import make_source_lineage, make_dataset_lineage, make_version_lineage
from .registry import DatasetCatalogRegistry
from .inventory import build_inventory_record, build_full_inventory, builtin_manifest, load_manifest
from .validation import DatasetValidator
from .governance import DatasetGovernance
from .readiness import ReadinessEngine
from .registration import manifest_fingerprint, delegate_to_model_foundation
from . import reports as _reports


class DatasetIntegrationError(RuntimeError):
    """Raised on hub misuse (no manifest/source supplied)."""


@dataclass(frozen=True)
class DatasetIntegrationOutcome:
    accepted: bool
    source: EegDatasetSource
    reason: str = ""
    dataset_record: object = None
    inventory: object = None
    validation: object = None
    governance: object = None
    readiness: object = None
    source_record: object = None
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    model_foundation_dataset_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted, "source": self.source.value, "reason": self.reason,
            "dataset": self.dataset_record.to_dict() if self.dataset_record else None,
            "validation": self.validation.to_dict() if self.validation else None,
            "governance": self.governance.to_dict() if self.governance else None,
            "readiness": self.readiness.to_dict() if self.readiness else None,
            "lineage_id": self.lineage_id, "audit_head": self.audit_head,
            "model_foundation_dataset_id": self.model_foundation_dataset_id,
        }


class DatasetIntegrationService:
    def __init__(self, *, lineage_tracker: Optional[LineageTracker] = None,
                 registry: Optional[DatasetCatalogRegistry] = None):
        self.lineage = lineage_tracker or LineageTracker()
        self.registry = registry or DatasetCatalogRegistry()
        self.validator = DatasetValidator()
        self.governance = DatasetGovernance()
        self.readiness_engine = ReadinessEngine()
        self._audit_logs: dict[str, ImmutableAuditLog] = {}
        self._outcomes: dict[str, DatasetIntegrationOutcome] = {}

    # --- inventory (DRP1-C) ---------------------------------------------------
    def inventory(self) -> list:
        return build_full_inventory()

    def audit_log_for(self, dataset_id: str) -> ImmutableAuditLog:
        return self._audit_logs[dataset_id]

    # --- register one dataset (DRP1-D..G) ------------------------------------
    def register(self, manifest_or_path=None, *, source: Optional[EegDatasetSource] = None,
                 dataset_key: Optional[str] = None, owner: str = "dataset-ops",
                 created_at: str = DETERMINISTIC_EPOCH) -> DatasetIntegrationOutcome:
        # resolve the manifest (built-in catalog or caller-supplied; never downloaded)
        if manifest_or_path is not None:
            manifest = load_manifest(manifest_or_path)
        elif source is not None:
            manifest = builtin_manifest(source)
        else:
            raise DatasetIntegrationError("supply a manifest/path or a built-in source")
        src = source or _coerce_source(manifest.get("source"))
        dataset_key = dataset_key or str(manifest.get("name") or src.value)

        inventory = build_inventory_record(manifest)
        validation = self.validator.validate(manifest, inventory)
        governance = self.governance.extract(manifest)
        manifest_fp = manifest_fingerprint(manifest)
        status = (InventoryStatus.REGISTERED if validation.ok else InventoryStatus.QUARANTINED)

        # --- identities + lineage chain: Source -> Dataset -> Version --------
        src_identity = mint_identity("dataset_source", {"source": src.value})
        source_id = src_identity.id
        source_node = self.lineage.record(make_source_lineage(source_id, source=src.value,
                                                             created_at=created_at))
        ds_identity = mint_identity("dataset", {
            "source": src.value, "dataset_key": dataset_key,
            "manifest_fingerprint": manifest_fp, "source_id": source_id})
        dataset_id = ds_identity.id
        dataset_node = self.lineage.record(make_dataset_lineage(
            dataset_id, source_id, source_node.lineage_id, manifest_fingerprint=manifest_fp,
            created_at=created_at))

        identity = DatasetIdentity(dataset_id=dataset_id, name=str(manifest.get("name", "")),
                                   source=src, identity_version=ds_identity.identity_version)
        state_sig = DatasetRecord.state_signature_of(identity=identity, inventory=inventory,
                                                     status=status, manifest_fingerprint=manifest_fp)
        version = DatasetVersion(version=DatasetVersion.compute(state_sig, None), previous=None,
                                 reason="registered", created_at=created_at)
        version_identity = mint_identity("dataset_version", {"dataset_id": dataset_id,
                                                            "version_key": version.version})
        version_node = self.lineage.record(make_version_lineage(
            version_identity.id, dataset_id, dataset_node.lineage_id, version=version.version,
            created_at=created_at))

        # --- integrate with the model-foundation connector (supported sources)
        mf_dataset_id = delegate_to_model_foundation(src, manifest, dataset_key=dataset_key)

        traceable = self.lineage.verify_chain(version_node.lineage_id)
        readiness = self.readiness_engine.assess(
            inventory=inventory, validation=validation, governance=governance,
            registered=True, traceable=traceable)

        # --- audit (shared ImmutableAuditLog) --------------------------------
        log = make_dataset_audit_log()
        self._audit_logs[dataset_id] = log
        log.append("source_inventoried", {"source_id": source_id, "source": src.value},
                   created_at=created_at)
        log.append("dataset_registered", {"dataset_id": dataset_id, "manifest_fp": manifest_fp,
                                          "status": status.value}, created_at=created_at)
        log.append("dataset_validated", {"validation_id": validation.validation_id,
                                         "ok": validation.ok}, created_at=created_at)
        log.append("dataset_governed", {"governance_id": governance.governance_id,
                                        "status": governance.status.value}, created_at=created_at)
        log.append("dataset_scored", {"readiness_id": readiness.readiness_id,
                                      "classification": readiness.classification.value,
                                      "score": readiness.score}, created_at=created_at)
        if mf_dataset_id:
            log.append("model_foundation_linked", {"model_foundation_dataset_id": mf_dataset_id},
                       created_at=created_at)

        record = DatasetRecord(
            identity=identity, inventory=inventory, version=version, status=status,
            manifest_fingerprint=manifest_fp, governance_id=governance.governance_id,
            validation_id=validation.validation_id, readiness_id=readiness.readiness_id,
            source_id=source_id, model_foundation_dataset_id=mf_dataset_id, owner=owner,
            created_at=created_at, lineage_id=version_node.lineage_id, audit_head=log.head)

        source_record = DatasetSourceRecord(
            source_id=source_id, source=src,
            display_name=str(manifest.get("name", src.value)),
            source_url=str((manifest.get("governance") or {}).get("source_url", "")),
            owner=governance.owner,
            attribution=governance.attribution, lineage_id=source_node.lineage_id)

        self._register_catalog(record, source_node.lineage_id, dataset_node.lineage_id,
                               version_node.lineage_id, log.head)
        outcome = DatasetIntegrationOutcome(
            accepted=True, source=src, reason="registered", dataset_record=record,
            inventory=inventory, validation=validation, governance=governance, readiness=readiness,
            source_record=source_record, lineage_id=version_node.lineage_id, audit_head=log.head,
            model_foundation_dataset_id=mf_dataset_id)
        self._outcomes[dataset_id] = outcome
        return outcome

    def register_all_mandatory(self, *, created_at: str = DETERMINISTIC_EPOCH) -> dict:
        out = {}
        for src in (EegDatasetSource.TUH_EEG, EegDatasetSource.CHB_MIT, EegDatasetSource.TEMPLE_EEG,
                    EegDatasetSource.SIENA_SCALP, EegDatasetSource.BONN):
            out[src.value] = self.register(source=src, created_at=created_at)
        return out

    # --- reporting (DRP1-J) ---------------------------------------------------
    def reports(self, outcome: DatasetIntegrationOutcome) -> dict:
        rec = outcome.dataset_record
        log = self._audit_logs[rec.dataset_id]
        return {
            "inventory_report": _reports.build_inventory_report([outcome.inventory]),
            "validation_report": _reports.build_validation_report(outcome.validation),
            "governance_report": _reports.build_governance_report(outcome.governance),
            "readiness_report": _reports.build_readiness_report(outcome.readiness),
            "registry_report": _reports.build_registry_report(self.registry),
            "audit_report": _reports.build_audit_report(log, subject=rec.dataset_id),
            "lineage_report": _reports.build_lineage_report(self.lineage, rec.lineage_id),
            "dataset_summary_report": _reports.build_dataset_summary_report(rec),
        }

    def inventory_report(self) -> dict:
        return _reports.build_inventory_report(self.inventory())

    def registry_report(self) -> dict:
        return _reports.build_registry_report(self.registry)

    # --- internals ------------------------------------------------------------
    def _register_catalog(self, record, source_lineage, dataset_lineage, version_lineage,
                          audit_head) -> None:
        if not self.registry.exists(record.source_id):
            self.registry.register(DatasetRegistryRecord(
                entity_kind=EntityKind.SOURCE, entity_id=record.source_id, status="inventoried",
                version="source", owner=record.owner, creation_date=record.created_at,
                audit_state=audit_head, lineage_id=source_lineage, source=record.source.value))
        self.registry.register(DatasetRegistryRecord(
            entity_kind=EntityKind.DATASET, entity_id=record.dataset_id, status=record.status.value,
            version=record.version.version, owner=record.owner, creation_date=record.created_at,
            audit_state=audit_head, lineage_id=dataset_lineage, source=record.source.value,
            dependencies=(record.source_id,)))
        version_entity = f"dataset_version+{record.version.version[:16]}"
        self.registry.register(DatasetRegistryRecord(
            entity_kind=EntityKind.VERSION, entity_id=version_entity, status=record.status.value,
            version=record.version.version, owner=record.owner, creation_date=record.created_at,
            audit_state=audit_head, lineage_id=version_lineage, source=record.source.value,
            dependencies=(record.dataset_id,)))


def _coerce_source(value) -> EegDatasetSource:
    try:
        return EegDatasetSource(str(value))
    except ValueError:
        return EegDatasetSource.OTHER


__all__ = ["DatasetIntegrationService", "DatasetIntegrationOutcome", "DatasetIntegrationError"]
