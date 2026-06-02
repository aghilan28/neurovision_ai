"""Tests for the validation subsystem and the validating ingestion pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from datasets.ingestion import ingest_edf_file
from datasets.ingestion.pipeline import IngestionError
from datasets.schemas.enums import RecordStatus, ValidationStatus
from datasets.tests._edf_fixtures import (
    EdfBuildSpec,
    SignalSpec,
    standard_eeg_spec,
    write_edf,
)
from datasets.validation import ValidationContext


def _codes(record):
    return {i.code for i in record.validation.issues}


def test_clean_edf_passes(make_edf):
    record = ingest_edf_file(make_edf(edf_plus=True))
    assert record.validation.status is ValidationStatus.PASSED
    assert record.status is RecordStatus.VALIDATED
    assert record.is_acceptable


def test_unsupported_format_raises_with_report(tmp_path):
    # BDF magic -> recognized but unsupported in V1.
    path = tmp_path / "x.bdf"
    path.write_bytes(b"\xffBIOSEMI" + b" " * 248 + b"\x00" * 16)
    with pytest.raises(IngestionError) as exc:
        ingest_edf_file(str(path))
    assert exc.value.report.status is ValidationStatus.FAILED
    assert {"UNSUPPORTED_FORMAT", "UNKNOWN_FORMAT"} & {i.code for i in exc.value.report.issues}


def test_unreadable_bytes_raise_parse_error(tmp_path):
    path = tmp_path / "garbage.edf"
    path.write_bytes(b"0" + b" " * 7 + b"not an edf header" * 20)
    with pytest.raises(IngestionError) as exc:
        ingest_edf_file(str(path))
    codes = {i.code for i in exc.value.report.issues}
    assert "EDF_PARSE_ERROR" in codes or "UNKNOWN_FORMAT" in codes


def test_integrity_mismatch_quarantines(tmp_path):
    path = write_edf(tmp_path / "rec.edf", standard_eeg_spec(edf_plus=True))
    # Truncate the data section to simulate corruption (header still declares 10 records).
    raw = Path(path).read_bytes()
    Path(path).write_bytes(raw[: len(raw) - 4000])
    record = ingest_edf_file(path)
    assert record.status is RecordStatus.QUARANTINED
    assert "FILE_INTEGRITY_MISMATCH" in _codes(record)


def test_missing_expected_channels_is_error(make_edf):
    path = make_edf(edf_plus=True, channels=("Fp1", "C3"))
    ctx = ValidationContext(expected_channels=("Fp1", "C3", "O2"))
    record = ingest_edf_file(path, context=ctx)
    assert record.status is RecordStatus.QUARANTINED
    assert "MISSING_EXPECTED_CHANNELS" in _codes(record)


def test_duplicate_detection_via_known_hashes(make_edf):
    path = make_edf(edf_plus=True)
    first = ingest_edf_file(path)
    ctx = ValidationContext(known_sha256=frozenset({first.raw_file.content_sha256}))
    second = ingest_edf_file(path, context=ctx)
    assert "DUPLICATE_RECORD" in _codes(second)
    # A warning, not an error: the record is still acceptable.
    assert second.is_acceptable


def test_non_uniform_sampling_warns(tmp_path):
    spec = EdfBuildSpec(
        signals=[SignalSpec("C3", 256.0), SignalSpec("ECG", 128.0)],
        num_records=4,
    )
    path = write_edf(tmp_path / "mixed.edf", spec)
    record = ingest_edf_file(path)
    assert "NON_UNIFORM_SAMPLING" in _codes(record)


def test_checks_run_recorded(make_edf):
    record = ingest_edf_file(make_edf(edf_plus=True))
    assert {"format", "integrity", "channels", "sampling", "metadata"} <= set(
        record.validation.checks_run
    )
    assert record.validation.validator_version


def test_missing_file_raises(tmp_path):
    with pytest.raises(IngestionError) as exc:
        ingest_edf_file(str(tmp_path / "does_not_exist.edf"))
    assert exc.value.report.issues[0].code == "FILE_NOT_FOUND"
