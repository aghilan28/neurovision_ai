"""Fixtures for dataset-intelligence tests.

Records are produced by the *real* V1-P1 ingestion path (write an EDF/EDF+ fixture,
then ``ingest_edf_file``), so the intelligence layer is tested against the genuine
``ValidatedEegRecord`` contract rather than hand-built stand-ins.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from datasets.ingestion import ingest_edf_file
from datasets.tests._edf_fixtures import EdfPlusAnnotation, standard_eeg_spec, write_edf


@dataclass
class RecordSpec:
    name: str
    patient_field: str
    channels: tuple[str, ...] = ("Fp1", "Fp2", "C3", "C4", "O1", "O2")
    sampling_rate_hz: float = 256.0
    duration_s: float = 20.0
    start_time: str = "14.30.00"
    annotations: list[EdfPlusAnnotation] = field(default_factory=list)


@pytest.fixture
def make_records(tmp_path):
    """Factory: list[RecordSpec] -> list[ValidatedEegRecord] (ingested)."""

    def _make(specs):
        records = []
        for i, spec in enumerate(specs):
            edf_spec = standard_eeg_spec(
                channels=spec.channels,
                sampling_rate_hz=spec.sampling_rate_hz,
                duration_s=spec.duration_s,
                edf_plus=True,
                patient_field=spec.patient_field,
                annotations=spec.annotations,
            )
            edf_spec.start_time = spec.start_time
            path = write_edf(tmp_path / f"{spec.name}_{i}.edf", edf_spec)
            records.append(ingest_edf_file(path))
        return records

    return _make


@pytest.fixture
def cohort(make_records):
    """A small, varied 3-patient cohort with annotations (one multi-recording patient)."""
    return make_records([
        RecordSpec("a", "P-1 M 01-JAN-1970 A",
                   annotations=[EdfPlusAnnotation(2.0, 1.0, "Seizure onset"),
                                EdfPlusAnnotation(8.0, 2.0, "GPD run")]),
        RecordSpec("b", "P-1 M 01-JAN-1970 A", duration_s=30.0, start_time="20.00.00",
                   annotations=[EdfPlusAnnotation(5.0, 1.0, "LPD")]),
        RecordSpec("c", "P-2 F 01-JAN-1980 B", channels=("Fp1", "C3", "O1"),
                   sampling_rate_hz=200.0, duration_s=15.0,
                   annotations=[EdfPlusAnnotation(3.0, None, "background")]),
        RecordSpec("d", "P-3 M 01-JAN-1990 C", duration_s=25.0),
    ])
