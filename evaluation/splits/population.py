"""Population adapters: build the ``patient_id -> record_ids`` mapping.

The split generator operates on a pure ``Mapping[str, Sequence[str]]`` (patient id
to record ids) so it is decoupled from datasets types and trivially testable. These
helpers build that mapping from the richer datasets artifacts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from evaluation._canonical import canonical_fingerprint


def patients_from_records(records: Sequence[object]) -> dict[str, list[str]]:
    """Build ``{patient_id: [record_id, ...]}`` from validated/registered records.

    Accepts any object exposing ``patient_id`` plus either ``file_id`` (registry
    entry) or ``session.recording_id`` / ``file_id`` (validated record). Record ids
    are de-duplicated and sorted for determinism.
    """
    mapping: dict[str, set[str]] = {}
    for r in records:
        patient_id = r.patient_id  # type: ignore[attr-defined]
        record_id = getattr(r, "file_id", None)
        if record_id is None:
            session = getattr(r, "session", None)
            record_id = getattr(session, "recording_id", None)
        if record_id is None:
            raise ValueError("record exposes neither file_id nor session.recording_id")
        mapping.setdefault(patient_id, set()).add(record_id)
    return {pid: sorted(recs) for pid, recs in mapping.items()}


def population_fingerprint(population: Mapping[str, Sequence[str]]) -> str:
    """Deterministic, order-independent fingerprint of a patient→records population."""
    members = sorted(
        [patient_id, sorted(record_ids)] for patient_id, record_ids in population.items()
    )
    return canonical_fingerprint({"population": members})
