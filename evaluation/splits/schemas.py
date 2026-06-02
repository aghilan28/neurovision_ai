"""Schemas for evaluation splits.

A split is defined entirely by its inputs (population, scheme, fractions/fold, base
seed, generator version), so it is reproducible and comparable. Partitions store
both the patient ids and the record ids assigned to them; patient-disjointness is a
structural property (a patient id appears in exactly one partition).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from evaluation._canonical import canonical_fingerprint, mint_id

#: Version of the split-generation logic (recorded on every split).
SPLIT_GENERATOR_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class Partition:
    """One partition of a split (e.g. ``train``/``val``/``test`` or a LOSO fold)."""

    name: str
    patient_ids: tuple[str, ...]
    record_ids: tuple[str, ...]

    @property
    def n_patients(self) -> int:
        return len(self.patient_ids)

    @property
    def n_records(self) -> int:
        return len(self.record_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "patient_ids": list(self.patient_ids),
            "record_ids": list(self.record_ids),
            "n_patients": self.n_patients,
            "n_records": self.n_records,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Partition:
        return cls(
            name=data["name"],
            patient_ids=tuple(data.get("patient_ids", ())),
            record_ids=tuple(data.get("record_ids", ())),
        )


@dataclass(frozen=True, slots=True)
class SplitSpec:
    """The reproducible specification of a split."""

    scheme: str  # "patient_disjoint" | "loso"
    base_seed: int
    fractions: dict[str, float] = field(default_factory=dict)  # for patient_disjoint
    fold_index: int | None = None  # for loso
    held_out_patient: str | None = None  # for loso
    generator_version: str = SPLIT_GENERATOR_VERSION
    dataset_id: str | None = None
    dataset_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scheme": self.scheme,
            "base_seed": self.base_seed,
            "fractions": self.fractions,
            "fold_index": self.fold_index,
            "held_out_patient": self.held_out_patient,
            "generator_version": self.generator_version,
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SplitSpec:
        return cls(
            scheme=data["scheme"],
            base_seed=int(data["base_seed"]),
            fractions=dict(data.get("fractions", {})),
            fold_index=data.get("fold_index"),
            held_out_patient=data.get("held_out_patient"),
            generator_version=data.get("generator_version", SPLIT_GENERATOR_VERSION),
            dataset_id=data.get("dataset_id"),
            dataset_version=data.get("dataset_version"),
        )


@dataclass(frozen=True, slots=True)
class SplitResult:
    """A generated split: its spec, partitions, and reproducible fingerprints."""

    spec: SplitSpec
    partitions: tuple[Partition, ...]
    population_fingerprint: str
    n_patients: int
    n_records: int
    created_at: str | None = None  # provenance only; excluded from fingerprint

    @property
    def partition_names(self) -> tuple[str, ...]:
        return tuple(p.name for p in self.partitions)

    def partition(self, name: str) -> Partition:
        for p in self.partitions:
            if p.name == name:
                return p
        raise KeyError(f"no partition named {name!r}")

    def all_patient_ids(self) -> tuple[str, ...]:
        out: list[str] = []
        for p in self.partitions:
            out.extend(p.patient_ids)
        return tuple(out)

    def _fingerprint_payload(self) -> dict[str, Any]:
        return {
            "spec": self.spec.to_dict(),
            "population_fingerprint": self.population_fingerprint,
            "partitions": [
                {
                    "name": p.name,
                    "patient_ids": sorted(p.patient_ids),
                    "record_ids": sorted(p.record_ids),
                }
                for p in sorted(self.partitions, key=lambda x: x.name)
            ],
        }

    @property
    def content_fingerprint(self) -> str:
        """Deterministic fingerprint of the split (excludes volatile timestamp)."""
        return canonical_fingerprint(self._fingerprint_payload())

    @property
    def split_id(self) -> str:
        """Content-derived split identifier."""
        return mint_id("split", self.content_fingerprint)

    def to_dict(self) -> dict[str, Any]:
        return {
            "split_id": self.split_id,
            "spec": self.spec.to_dict(),
            "partitions": [p.to_dict() for p in self.partitions],
            "population_fingerprint": self.population_fingerprint,
            "n_patients": self.n_patients,
            "n_records": self.n_records,
            "content_fingerprint": self.content_fingerprint,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SplitResult:
        return cls(
            spec=SplitSpec.from_dict(data["spec"]),
            partitions=tuple(Partition.from_dict(p) for p in data.get("partitions", [])),
            population_fingerprint=data["population_fingerprint"],
            n_patients=int(data["n_patients"]),
            n_records=int(data["n_records"]),
            created_at=data.get("created_at"),
        )
