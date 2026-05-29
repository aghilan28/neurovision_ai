"""Lineage records, version bundles, and the lineage tracker.

A ``VersionBundle`` is the canonical set of version coordinates the whole platform
pins against. A ``LineageRecord`` wraps a bundle plus typed inputs/outputs and
parent links into a content-addressed, auditable node. ``LineageTracker`` stores
nodes and can walk/verify a lineage chain.

Lineage IDs are *content-derived* (a hash of kind + versions + inputs + outputs +
parents). ``created_at`` is recorded as non-hashed metadata so wall-clock time
never perturbs reproducibility (NR-10).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Mapping, Optional

from ..version import LINEAGE_VERSION, DETERMINISTIC_EPOCH
from ..provenance import content_id


@dataclass(frozen=True)
class VersionBundle:
    """The canonical version coordinates pinned by every lineage record.

    Fields cover the full V1 pipeline. Unknown/not-yet-applicable stages are None
    (e.g. evaluation_version before evaluation runs). The
    ``dataset_intelligence_version`` is the V1-P3 coordinate; it is carried as a
    first-class field so lineage stays compatible with the dataset-intelligence
    layer even though V1-P5/P6 do not implement it.
    """

    dataset_version: Optional[str] = None
    dataset_intelligence_version: Optional[str] = None
    preprocessing_version: Optional[str] = None
    split_version: Optional[str] = None
    training_version: Optional[str] = None
    model_version: Optional[str] = None
    architecture_version: Optional[str] = None
    evaluation_version: Optional[str] = None
    benchmark_version: Optional[str] = None
    calibration_version: Optional[str] = None
    conformal_version: Optional[str] = None
    coverage_version: Optional[str] = None
    risk_version: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def merged(self, **updates: Any) -> "VersionBundle":
        data = self.to_dict()
        data.update({k: v for k, v in updates.items() if k in data})
        return VersionBundle(**data)


@dataclass(frozen=True)
class LineageRecord:
    """A content-addressed provenance node."""

    lineage_id: str
    kind: str
    versions: dict
    inputs: dict
    outputs: dict
    parents: tuple[str, ...]
    created_at: str
    lineage_version: str = LINEAGE_VERSION

    def to_dict(self) -> dict:
        return {
            "lineage_id": self.lineage_id,
            "kind": self.kind,
            "lineage_version": self.lineage_version,
            "versions": self.versions,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "parents": list(self.parents),
            "created_at": self.created_at,
        }


def make_lineage_record(
    kind: str,
    versions: VersionBundle | Mapping[str, Any],
    inputs: Mapping[str, Any],
    outputs: Mapping[str, Any],
    parents: tuple[str, ...] = (),
    created_at: str = DETERMINISTIC_EPOCH,
) -> LineageRecord:
    """Build a content-addressed lineage record (id excludes ``created_at``)."""
    version_dict = versions.to_dict() if isinstance(versions, VersionBundle) else dict(versions)
    payload = {
        "kind": kind,
        "versions": version_dict,
        "inputs": dict(inputs),
        "outputs": dict(outputs),
        "parents": list(parents),
    }
    lineage_id = content_id("lineage", payload)
    return LineageRecord(
        lineage_id=lineage_id,
        kind=kind,
        versions=version_dict,
        inputs=dict(inputs),
        outputs=dict(outputs),
        parents=tuple(parents),
        created_at=created_at,
    )


class LineageTracker:
    """In-memory lineage graph with optional artifact persistence."""

    def __init__(self) -> None:
        self._records: dict[str, LineageRecord] = {}

    def record(self, rec: LineageRecord) -> LineageRecord:
        self._records[rec.lineage_id] = rec
        return rec

    def get(self, lineage_id: str) -> LineageRecord:
        if lineage_id not in self._records:
            raise KeyError(f"unknown lineage_id {lineage_id!r}")
        return self._records[lineage_id]

    def exists(self, lineage_id: str) -> bool:
        return lineage_id in self._records

    def chain(self, lineage_id: str) -> list[LineageRecord]:
        """Return the lineage node and all ancestors (depth-first, de-duplicated)."""
        seen: dict[str, LineageRecord] = {}
        stack = [lineage_id]
        order: list[LineageRecord] = []
        while stack:
            lid = stack.pop()
            if lid in seen:
                continue
            rec = self.get(lid)
            seen[lid] = rec
            order.append(rec)
            stack.extend(rec.parents)
        return order

    def verify_chain(self, lineage_id: str) -> bool:
        """True iff the node and every ancestor it references exist (no broken links)."""
        try:
            for rec in self.chain(lineage_id):
                for parent in rec.parents:
                    if not self.exists(parent):
                        return False
        except KeyError:
            return False
        return True

    def all(self) -> dict[str, LineageRecord]:
        return dict(self._records)

    def to_dict(self) -> dict:
        return {
            "lineage_version": LINEAGE_VERSION,
            "n_records": len(self._records),
            "records": {lid: rec.to_dict() for lid, rec in sorted(self._records.items())},
        }
