"""Dataset Integration domain entities + closed vocabularies (DRP1-B).

Pure, JSON-able, content-hashable records and closed enumerations describing the external
EEG dataset lifecycle. No I/O, no orchestration. Mirrors the established platform
domain-model shape (NR-6). These records describe *external corpora* (inventory +
governance + readiness) — they never materialize the recordings.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..version import (
    DATASET_DOMAIN_VERSION, DATASET_GOVERNANCE_VERSION, DATASET_READINESS_VERSION,
    DATASET_REGISTRY_VERSION, DATASET_VALIDATION_VERSION, DETERMINISTIC_EPOCH,
)


# =============================================================================
# Closed vocabularies
# =============================================================================
class EegDatasetSource(str, Enum):
    """The closed set of external EEG corpora the platform can inventory."""

    TUH_EEG = "tuh_eeg"
    CHB_MIT = "chb_mit"
    TEMPLE_EEG = "temple_eeg"
    SIENA_SCALP = "siena_scalp"
    BONN = "bonn"
    OTHER = "other"


class DatasetFormat(str, Enum):
    EDF = "edf"
    EDF_PLUS = "edf_plus"
    BDF = "bdf"
    BDF_PLUS = "bdf_plus"
    FIF = "fif"
    SET = "set"
    ASCII = "ascii"
    CSV = "csv"
    OTHER = "other"


class LicenseType(str, Enum):
    """License *category* (metadata only — no legal interpretation)."""

    OPEN_ACCESS = "open_access"
    DATA_USE_AGREEMENT = "data_use_agreement"
    RESEARCH_ONLY = "research_only"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class InventoryStatus(str, Enum):
    INVENTORIED = "inventoried"
    REGISTERED = "registered"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"


class ValidationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class GovernanceStatus(str, Enum):
    DOCUMENTED = "documented"
    INCOMPLETE = "incomplete"
    MISSING = "missing"


class ReadinessClass(str, Enum):
    NOT_READY = "NOT_READY"
    PARTIALLY_READY = "PARTIALLY_READY"
    READY = "READY"


class EntityKind(str, Enum):
    SOURCE = "dataset_source"
    DATASET = "dataset"
    VERSION = "dataset_version"


# =============================================================================
# Versioning
# =============================================================================
@dataclass(frozen=True)
class DatasetVersion:
    version: str
    previous: Optional[str]
    reason: str
    created_at: str = DETERMINISTIC_EPOCH

    @staticmethod
    def compute(state_signature: str, previous: Optional[str]) -> str:
        return hash_obj({"state": state_signature, "previous": previous})

    def to_dict(self) -> dict:
        return {"version": self.version, "previous": self.previous, "reason": self.reason,
                "created_at": self.created_at}


# =============================================================================
# Identity + source
# =============================================================================
@dataclass(frozen=True)
class DatasetIdentity:
    dataset_id: str
    name: str
    source: EegDatasetSource
    identity_version: str
    domain_version: str = DATASET_DOMAIN_VERSION

    def to_dict(self) -> dict:
        return {"dataset_id": self.dataset_id, "name": self.name, "source": self.source.value,
                "identity_version": self.identity_version, "domain_version": self.domain_version}


@dataclass(frozen=True)
class DatasetSourceRecord:
    source_id: str
    source: EegDatasetSource
    display_name: str
    source_url: str
    owner: str
    attribution: str
    lineage_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {"source_id": self.source_id, "source": self.source.value,
                "display_name": self.display_name, "source_url": self.source_url,
                "owner": self.owner, "attribution": self.attribution, "lineage_id": self.lineage_id}


# =============================================================================
# Validation / governance / readiness projections
# =============================================================================
@dataclass(frozen=True)
class DatasetValidationRecord:
    validation_id: str
    ok: bool
    findings: tuple                      # (check, severity, passed, detail)
    validation_version: str = DATASET_VALIDATION_VERSION

    @property
    def n_checks(self) -> int:
        return len(self.findings)

    def signature(self) -> str:
        return hash_obj({"ok": self.ok,
                         "findings": [[c, s, bool(p)] for c, s, p, _ in self.findings]})

    def to_dict(self) -> dict:
        return {"validation_id": self.validation_id, "ok": self.ok, "n_checks": self.n_checks,
                "findings": [{"check": c, "severity": s, "passed": bool(p), "detail": d}
                             for c, s, p, d in self.findings],
                "validation_version": self.validation_version, "signature": self.signature()}


@dataclass(frozen=True)
class DatasetGovernanceRecord:
    governance_id: str
    license_name: str
    license_type: LicenseType
    usage_restrictions: tuple
    research_restrictions: tuple
    attribution: str
    owner: str
    source_url: str
    compliance_metadata: dict
    status: GovernanceStatus
    governance_version: str = DATASET_GOVERNANCE_VERSION

    def to_dict(self) -> dict:
        return {"governance_id": self.governance_id, "license_name": self.license_name,
                "license_type": self.license_type.value,
                "usage_restrictions": list(self.usage_restrictions),
                "research_restrictions": list(self.research_restrictions),
                "attribution": self.attribution, "owner": self.owner, "source_url": self.source_url,
                "compliance_metadata": dict(sorted(self.compliance_metadata.items())),
                "status": self.status.value, "governance_version": self.governance_version}


@dataclass(frozen=True)
class DatasetReadinessRecord:
    readiness_id: str
    score: float
    classification: ReadinessClass
    dimensions: dict
    findings: tuple
    readiness_version: str = DATASET_READINESS_VERSION

    def to_dict(self) -> dict:
        return {"readiness_id": self.readiness_id, "score": self.score,
                "classification": self.classification.value,
                "dimensions": dict(sorted(self.dimensions.items())),
                "findings": list(self.findings), "readiness_version": self.readiness_version}


# =============================================================================
# Inventory + dataset records
# =============================================================================
@dataclass(frozen=True)
class DatasetInventoryRecord:
    """An inventory entry for an external corpus (inventory only — never downloaded)."""

    inventory_id: str
    source: EegDatasetSource
    name: str
    version_label: str
    location: str
    format: DatasetFormat
    license_name: str
    size: dict                            # {recordings, hours, bytes_estimate, ...}
    channels: tuple
    sampling_frequency: Optional[float]
    n_recordings: int
    n_patients: int
    metadata_completeness: float
    status: InventoryStatus
    downloaded: bool = False

    def to_dict(self) -> dict:
        return {"inventory_id": self.inventory_id, "source": self.source.value, "name": self.name,
                "version_label": self.version_label, "location": self.location,
                "format": self.format.value, "license_name": self.license_name, "size": self.size,
                "channels": list(self.channels), "sampling_frequency": self.sampling_frequency,
                "n_recordings": self.n_recordings, "n_patients": self.n_patients,
                "metadata_completeness": self.metadata_completeness, "status": self.status.value,
                "downloaded": self.downloaded}


@dataclass(frozen=True)
class DatasetRecord:
    """An **immutable** registered external-dataset record (inventory/governance asset).

    Carries no recording arrays — only the governed metadata + cross-references to the
    validation/governance/readiness projections, the lineage node, the audit head, and
    (when the model-foundation connector supports the source) its DatasetRecord id."""

    identity: DatasetIdentity
    inventory: DatasetInventoryRecord
    version: DatasetVersion
    status: InventoryStatus
    manifest_fingerprint: str
    governance_id: Optional[str] = None
    validation_id: Optional[str] = None
    readiness_id: Optional[str] = None
    source_id: Optional[str] = None
    model_foundation_dataset_id: Optional[str] = None
    owner: str = "dataset-ops"
    created_at: str = DETERMINISTIC_EPOCH
    lineage_id: Optional[str] = None
    audit_head: Optional[str] = None
    domain_version: str = DATASET_DOMAIN_VERSION

    @property
    def dataset_id(self) -> str:
        return self.identity.dataset_id

    @property
    def source(self) -> EegDatasetSource:
        return self.identity.source

    @staticmethod
    def state_signature_of(*, identity, inventory, status, manifest_fingerprint) -> str:
        return hash_obj({"dataset_id": identity.dataset_id, "source": identity.source.value,
                         "inventory": inventory.to_dict(), "status": status.value,
                         "manifest_fingerprint": manifest_fingerprint})

    def state_signature(self) -> str:
        return self.state_signature_of(identity=self.identity, inventory=self.inventory,
                                       status=self.status,
                                       manifest_fingerprint=self.manifest_fingerprint)

    def to_dict(self) -> dict:
        return {
            "identity": self.identity.to_dict(), "dataset_id": self.dataset_id,
            "source": self.source.value, "inventory": self.inventory.to_dict(),
            "version": self.version.to_dict(), "status": self.status.value,
            "manifest_fingerprint": self.manifest_fingerprint, "governance_id": self.governance_id,
            "validation_id": self.validation_id, "readiness_id": self.readiness_id,
            "source_id": self.source_id, "model_foundation_dataset_id": self.model_foundation_dataset_id,
            "owner": self.owner, "created_at": self.created_at, "lineage_id": self.lineage_id,
            "audit_head": self.audit_head, "domain_version": self.domain_version,
            "state_signature": self.state_signature(),
        }


# =============================================================================
# Registry / audit / lineage projections
# =============================================================================
@dataclass
class DatasetRegistryRecord:
    entity_kind: EntityKind
    entity_id: str
    status: str
    version: str
    owner: str
    creation_date: str
    audit_state: str
    lineage_id: str
    source: Optional[str] = None
    dependencies: tuple = ()
    registry_version: str = DATASET_REGISTRY_VERSION

    def content_signature(self) -> str:
        return hash_obj({"entity_kind": self.entity_kind.value, "entity_id": self.entity_id,
                         "status": self.status, "version": self.version,
                         "lineage_id": self.lineage_id, "audit_state": self.audit_state})

    def to_dict(self) -> dict:
        return {"entity_kind": self.entity_kind.value, "entity_id": self.entity_id,
                "status": self.status, "version": self.version, "owner": self.owner,
                "creation_date": self.creation_date, "audit_state": self.audit_state,
                "lineage_id": self.lineage_id, "source": self.source,
                "dependencies": list(self.dependencies), "registry_version": self.registry_version,
                "content_signature": self.content_signature()}


@dataclass(frozen=True)
class DatasetAuditRecord:
    seq: int
    kind: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: str = DETERMINISTIC_EPOCH

    def to_dict(self) -> dict:
        return {"seq": self.seq, "kind": self.kind, "payload": self.payload,
                "prev_hash": self.prev_hash, "event_hash": self.event_hash,
                "created_at": self.created_at}


@dataclass(frozen=True)
class DatasetLineageRecord:
    lineage_id: str
    kind: str
    parents: tuple = ()

    def to_dict(self) -> dict:
        return {"lineage_id": self.lineage_id, "kind": self.kind, "parents": list(self.parents)}


__all__ = [
    "EegDatasetSource", "DatasetFormat", "LicenseType", "InventoryStatus", "ValidationSeverity",
    "GovernanceStatus", "ReadinessClass", "EntityKind", "DatasetVersion", "DatasetIdentity",
    "DatasetSourceRecord", "DatasetValidationRecord", "DatasetGovernanceRecord",
    "DatasetReadinessRecord", "DatasetInventoryRecord", "DatasetRecord", "DatasetRegistryRecord",
    "DatasetAuditRecord", "DatasetLineageRecord",
]
