"""Persistence *integrity* validation (DRP4-J, post-build).

Reuses ``ml.validation.ValidationReport`` to produce the mandated checks over a finalized,
persisted-and-recovered snapshot: storage / registry / audit / lineage / execution / recovery
/ version / traceability integrity. The result shape matches the rest of the platform (NR-6).
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity
from ..models.domain import StorageVersion

# the lineage kinds that prove a persisted snapshot traces to the patient
_REQUIRED_CHAIN_KINDS = {
    "patient", "case", "feature", "dataset", "model", "prediction", "serving_execution",
    "serving_response", "persistence_record",
}


class PersistenceIntegrityValidator:
    """Runs the mandated persistence integrity checks."""

    def validate(self, *, record: Any, recovery: Any, engine: Any, lineage_tracker: Any,
                 audit_log: Any, storage_records: Any = ()) -> ValidationReport:
        report = ValidationReport()

        # --- storage integrity (every persisted object still verifies on disk) -
        store_ok = all(engine.verify(sr) for sr in storage_records) if storage_records else False
        report.add("storage_integrity", bool(store_ok and record.lineage_storage.n_nodes > 0),
                   f"n_objects={len(storage_records)} verified={store_ok}")

        # --- registry integrity ---
        report.add("registry_integrity",
                   len(record.registry_storage) > 0
                   and all(r.fingerprint for r in record.registry_storage),
                   f"registries={[r.registry_name for r in record.registry_storage]}")

        # --- audit integrity ---
        report.add("audit_integrity",
                   len(record.audit_storage) > 0 and all(a.head for a in record.audit_storage),
                   f"logs={[a.log_name for a in record.audit_storage]}")

        # --- lineage integrity ---
        report.add("lineage_integrity",
                   record.lineage_storage.n_nodes > 0 and bool(record.lineage_id),
                   f"n_nodes={record.lineage_storage.n_nodes}")

        # --- execution integrity ---
        report.add("execution_integrity",
                   all(e.fingerprint for e in record.execution_storage),
                   f"streams={[e.history_kind for e in record.execution_storage]}")

        # --- recovery integrity (cold-restart recovery succeeded + verified) --
        report.add("recovery_integrity",
                   recovery.ok and recovery.anchor_verified
                   and all(p for _, p, _ in recovery.checks),
                   f"status={recovery.status.value} anchor_verified={recovery.anchor_verified}")

        # --- version integrity ---
        try:
            expected = StorageVersion.compute(record.state_signature(), record.version.previous)
            report.add("version_integrity", record.version.version == expected,
                       f"recorded={record.version.version} expected={expected}")
        except Exception as exc:  # pragma: no cover - defensive
            report.add("version_integrity", False, f"error: {exc}")

        # --- audit chain of the persistence record itself ---
        try:
            ok = audit_log.verify() and record.audit_head == audit_log.head
            report.add("persistence_audit_integrity", bool(ok),
                       f"chain_verified={audit_log.verify()} head_match={record.audit_head == audit_log.head}")
        except Exception as exc:
            report.add("persistence_audit_integrity", False, f"error: {exc}")

        # --- traceability integrity (persistence node chain reaches the patient) -
        try:
            ids_ok = validate_identity(record.persistence_id, "persistence_record")[0]
            chain_ok = bool(record.lineage_id) and lineage_tracker.verify_chain(record.lineage_id)
            kinds = ({r.kind for r in lineage_tracker.chain(record.lineage_id)}
                     if record.lineage_id else set())
            reaches = _REQUIRED_CHAIN_KINDS <= kinds
            report.add("traceability_integrity", bool(ids_ok and chain_ok and reaches),
                       f"chain_ok={chain_ok} reaches_patient={reaches}")
        except Exception as exc:
            report.add("traceability_integrity", False, f"error: {exc}")

        return report


__all__ = ["PersistenceIntegrityValidator"]
