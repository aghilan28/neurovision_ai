"""Tests for canonical metadata extraction."""

from __future__ import annotations

from datasets._canonical import sha256_file
from datasets.ingestion import read_edf
from datasets.ingestion.signature import detect_format
from datasets.metadata import extract_metadata, extract_patient, extract_session
from datasets.schemas.enums import ChannelType, FileFormat


def _extract(path):
    reading = read_edf(path, materialize_signals=False)
    fmt = detect_format(path)
    sha = sha256_file(path)
    md = extract_metadata(reading, content_sha256=sha, file_format=fmt)
    return md, sha


def test_identifiers_are_content_derived_and_deterministic(make_edf):
    path = make_edf(edf_plus=True)
    md1, sha = _extract(path)
    md2, _ = _extract(path)
    assert md1.file_id == f"edf-{sha[:16]}"
    assert md1.recording_id == f"rec-{sha[:16]}"
    assert md1.file_id == md2.file_id
    assert md1.patient_id == md2.patient_id


def test_edf_plus_patient_and_dates_parsed(make_edf):
    path = make_edf(edf_plus=True, patient_field="P-100 M 02-MAY-1951 Test")
    md, sha = _extract(path)
    patient = extract_patient(md, content_sha256=sha)
    assert md.file_format in (FileFormat.EDF_PLUS_C, FileFormat.EDF_PLUS_D)
    assert patient.sex == "M"
    assert patient.birthdate_iso == "1951-05-02"
    # Recording field carries EDF+ Startdate 02-MAR-2002.
    assert md.recording_date_iso == "2002-03-02"
    assert md.extra["patient_identity_present"] is True


def test_session_combines_date_and_time(make_edf):
    path = make_edf(edf_plus=True)
    md, _ = _extract(path)
    session = extract_session(md)
    assert session.start_datetime_iso == "2002-03-02T14:30:00"
    assert session.duration_seconds == 10.0


def test_channel_types_classified(make_edf):
    path = make_edf(edf_plus=True, channels=("Fp1", "C3", "O2"))
    md, _ = _extract(path)
    types = {c.label: c.channel_type for c in md.channels}
    assert types["FP1"] is ChannelType.EEG
    assert types["C3"] is ChannelType.EEG
    assert any(c.channel_type is ChannelType.ANNOTATION for c in md.channels)
    assert md.data_channel_count == 3
    assert md.is_uniform_sampling


def test_missing_patient_identity_marked_for_plain_edf(tmp_path):
    from datasets.tests._edf_fixtures import EdfBuildSpec, SignalSpec, write_edf

    spec = EdfBuildSpec(
        signals=[SignalSpec("C3", 100.0)],
        num_records=2,
        patient_field="X",  # explicitly anonymous
        edf_plus=False,
    )
    path = write_edf(tmp_path / "anon.edf", spec)
    md, _ = _extract(path)
    assert md.extra["patient_identity_present"] is False


def test_metadata_round_trips_through_dict(make_edf):
    from datasets.schemas import MetadataRecord

    path = make_edf(edf_plus=True)
    md, _ = _extract(path)
    restored = MetadataRecord.from_dict(md.to_dict())
    assert restored.to_dict() == md.to_dict()
