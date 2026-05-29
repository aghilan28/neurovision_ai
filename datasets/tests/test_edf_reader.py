"""Tests for the pure-Python EDF/EDF+ reader."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from datasets.ingestion import read_edf, read_edf_header
from datasets.ingestion.edf_reader import EdfReadError
from datasets.tests._edf_fixtures import (
    EdfBuildSpec,
    SignalSpec,
    standard_eeg_spec,
    write_edf,
)


def test_reads_header_fields(make_edf):
    path = make_edf(edf_plus=True)
    header = read_edf_header(path)
    assert header.num_signals == 7  # 6 EEG + 1 annotation channel
    assert header.is_edf_plus
    assert header.record_duration_seconds == 1.0
    assert header.num_data_records == 10


def test_reads_signals_with_correct_shape_and_order(make_edf):
    path = make_edf(channels=("Fp1", "Fp2", "C3"), sampling_rate_hz=200.0, duration_s=5.0)
    reading = read_edf(path)
    assert reading.signal_order[:3] == ("Fp1", "Fp2", "C3")
    # 200 Hz * 5 s = 1000 samples per data channel
    assert reading.signals["Fp1"].shape == (1000,)
    assert reading.signals["Fp1"].dtype == np.float64


def test_physical_values_recovered_within_quantization(tmp_path):
    # A known ramp signal should round-trip within one quantization step.
    sr = 100.0
    samples = np.linspace(-100.0, 100.0, int(sr * 2), dtype=np.float64)
    spec = EdfBuildSpec(
        signals=[SignalSpec("C3", sr, physical_min=-200.0, physical_max=200.0, samples=samples)],
        record_duration_seconds=1.0,
        num_records=2,
    )
    path = write_edf(tmp_path / "ramp.edf", spec)
    reading = read_edf(path)
    recovered = reading.signals["C3"]
    step = (200.0 - (-200.0)) / (2047 - (-2048))
    assert np.max(np.abs(recovered - samples)) <= step


def test_materialize_signals_false_skips_arrays_but_keeps_annotations(edf_plus_with_annotations):
    reading = read_edf(edf_plus_with_annotations, load_signals=True, materialize_signals=False)
    assert reading.signals == {}
    assert len(reading.annotations) == 2


def test_annotations_parsed_with_onset_and_duration(edf_plus_with_annotations):
    reading = read_edf(edf_plus_with_annotations)
    texts = {a[2]: (a[0], a[1]) for a in reading.annotations}
    assert texts["Seizure onset"] == (2.0, 1.5)
    assert texts["Artifact"] == (7.25, None)


def test_record_onsets_recovered(make_edf):
    path = make_edf(edf_plus=True, duration_s=4.0)
    reading = read_edf(path)
    assert reading.record_onsets == (0.0, 1.0, 2.0, 3.0)


def test_unknown_record_count_minus_one_is_resolved(tmp_path):
    spec = standard_eeg_spec(duration_s=3.0)
    spec.num_records = 3
    path = write_edf(tmp_path / "rec.edf", spec)
    # Corrupt only the num_data_records field to -1 (allowed by EDF).
    raw = bytearray(Path(path).read_bytes())
    raw[236:244] = b"-1      "
    Path(path).write_bytes(bytes(raw))
    reading = read_edf(path)
    # 3 records of data are present and should be recovered from file size.
    assert reading.header.record_size_samples > 0
    assert reading.signals["Fp1"].shape[0] == int(256 * 1.0) * 3


def test_truncated_header_raises(tmp_path):
    path = tmp_path / "tiny.edf"
    path.write_bytes(b"0" + b" " * 50)  # far shorter than 256 bytes
    with pytest.raises(EdfReadError) as exc:
        read_edf_header(str(path))
    assert exc.value.code == "HEADER_TOO_SHORT"


def test_non_numeric_header_field_raises(tmp_path):
    path = write_edf(tmp_path / "rec.edf", standard_eeg_spec())
    raw = bytearray(Path(path).read_bytes())
    raw[252:256] = b"abcd"  # number-of-signals field is not an int
    Path(path).write_bytes(bytes(raw))
    with pytest.raises(EdfReadError):
        read_edf_header(str(path))
