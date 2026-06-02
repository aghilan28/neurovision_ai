"""Shared fixtures for the datasets test suite."""

from __future__ import annotations

import pytest

from datasets.tests._edf_fixtures import (
    EdfPlusAnnotation,
    write_edf,
)
from datasets.tests._edf_fixtures import (
    standard_eeg_spec as _standard_eeg_spec,
)


@pytest.fixture
def make_edf(tmp_path):
    """Factory writing a standard EEG EDF/EDF+ file and returning its path."""

    def _make(name="rec.edf", **kwargs):
        spec = _standard_eeg_spec(**kwargs)
        return write_edf(tmp_path / name, spec)

    return _make


@pytest.fixture
def edf_plus_with_annotations(tmp_path):
    spec = _standard_eeg_spec(
        edf_plus=True,
        annotations=[
            EdfPlusAnnotation(2.0, 1.5, "Seizure onset"),
            EdfPlusAnnotation(7.25, None, "Artifact"),
        ],
    )
    return write_edf(tmp_path / "rec_plus.edf", spec)
