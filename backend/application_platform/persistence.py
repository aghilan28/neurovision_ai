"""``backend/application_platform/persistence.py`` — durable application state (DBE-4).

Wires the application lifecycle to the **existing** DRP-4 persistence platform so uploads,
predictions, reports, analyses, readiness, and the duplicate index survive a cold restart.

It REUSES ``backend.persistence_platform.StorageEngine`` (the durable, content-addressed,
checksum-verified filesystem JSON store) — **no parallel persistence system, no new database**.
Each accepted analysis is serialized to durable JSON keyed by its analysis id; on startup the
store is replayed to reconstruct the in-memory views (uploads / analyses / reports / duplicate
index) and to re-register the registry records, so retrieval after restart uses persisted
state (not in-memory reconstruction of a live workflow).

Layout (under ``<persistence_root>``, default ``<workspace>/app_state``):

    app.analyses/<analysis_id>.json   -> the full serialized AnalysisOutcome (+ report payloads
                                          + duplicate index entry + model_info snapshot)

The serialized outcome is the single source of truth for recovery; reconstruction uses the
domain ``from_dict`` methods (added in DBE-4). Audit + lineage **references** are carried inside
the persisted records (each record already stores its ``audit_head`` / ``lineage_id``), so the
Dataset -> Upload -> Prediction -> Report -> Audit -> Lineage references survive restart.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from backend.persistence_platform import StorageEngine

from .models.domain import (
    AnalysisRecord, PredictionRequestRecord, PredictionResultRecord, ReadinessRecord,
    ReportRecord, UploadRecord, ValidationRecord, WorkflowRecord,
)

_ANALYSES_NS = "app.analyses"


@dataclass
class RecoveryReport:
    """Deterministic record of what a cold-restart recovery restored."""

    recovered: bool
    n_analyses: int
    n_uploads: int
    n_reports: int
    analysis_ids: tuple = ()
    errors: tuple = ()

    @property
    def ok(self) -> bool:
        return self.recovered and not self.errors

    def to_dict(self) -> dict:
        return {"recovered": self.recovered, "n_analyses": self.n_analyses,
                "n_uploads": self.n_uploads, "n_reports": self.n_reports,
                "analysis_ids": list(self.analysis_ids), "ok": self.ok,
                "errors": list(self.errors)}


def serialize_outcome(outcome, report_payloads: dict, *, content_hash: str,
                      upload_id: str, model_info: dict) -> dict:
    """Serialize an accepted AnalysisOutcome + its report payloads for durable storage."""
    return {
        "analysis_id": outcome.analysis.analysis_id,
        "outcome": outcome.to_dict(),
        "report_payloads": report_payloads,
        "duplicate_index": {"content_hash": content_hash, "upload_id": upload_id,
                            "analysis_id": outcome.analysis.analysis_id},
        "model_info": dict(model_info),
    }


class ApplicationStateStore:
    """Durable store + recovery for application state (reuses the DRP-4 StorageEngine)."""

    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.engine = StorageEngine(self.root)

    # --- persist -------------------------------------------------------------
    def persist_analysis(self, payload: dict) -> str:
        """Durably store one accepted analysis payload; return the storage checksum."""
        analysis_id = payload["analysis_id"]
        record = self.engine.put(_ANALYSES_NS, analysis_id, payload)
        return record.checksum

    def has_any(self) -> bool:
        return bool(self.engine.list_keys(_ANALYSES_NS))

    def analysis_ids(self) -> list:
        return self.engine.list_keys(_ANALYSES_NS)

    def load_payload(self, analysis_id: str) -> dict:
        return self.engine.get(_ANALYSES_NS, analysis_id)

    def load_all_payloads(self) -> list:
        return [self.engine.get(_ANALYSES_NS, aid) for aid in self.analysis_ids()]


def reconstruct_outcome(outcome_dict: dict):
    """Rebuild a retrieval-ready AnalysisOutcome from its serialized dict.

    Returns an object exposing the same attributes the retrieval API + Track-4 ops read:
    ``accepted``, ``upload``, ``analysis``, ``prediction_request``, ``prediction_result``,
    ``report_record``, ``readiness``, ``validation``, ``workflow``, ``duplicate_classification``,
    ``is_duplicate`` — reconstructed from persisted state, not from a live workflow.
    """
    # imported here to avoid a circular import at module load (service imports this module)
    from .service import AnalysisOutcome

    def _maybe(record_cls, key):
        d = outcome_dict.get(key)
        return record_cls.from_dict(d) if d else None

    return AnalysisOutcome(
        accepted=bool(outcome_dict.get("accepted", True)),
        upload=UploadRecord.from_dict(outcome_dict["upload"]),
        workflow=_maybe(WorkflowRecord, "workflow"),
        analysis=_maybe(AnalysisRecord, "analysis"),
        prediction_request=_maybe(PredictionRequestRecord, "prediction_request"),
        prediction_result=_maybe(PredictionResultRecord, "prediction_result"),
        report_record=_maybe(ReportRecord, "report"),
        readiness=_maybe(ReadinessRecord, "readiness"),
        validation=_maybe(ValidationRecord, "validation"),
        reason=outcome_dict.get("reason", ""),
        duplicate_classification=outcome_dict.get("duplicate_classification", "NEW_UPLOAD"),
        is_duplicate=bool(outcome_dict.get("is_duplicate", False)))


def default_persistence_root(workspace_dir: Optional[str]) -> Optional[str]:
    """Resolve the persistence root from the workspace dir (or ``NV_PERSISTENCE_DIR``)."""
    env = os.environ.get("NV_PERSISTENCE_DIR")
    if env:
        return env
    if workspace_dir:
        return os.path.join(workspace_dir, "app_state")
    return None


__all__ = ["RecoveryReport", "ApplicationStateStore", "serialize_outcome",
           "reconstruct_outcome", "default_persistence_root"]
