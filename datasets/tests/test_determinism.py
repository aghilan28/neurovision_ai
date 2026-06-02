"""Determinism & reproducibility guarantees for the data foundation.

These encode the cross-version invariants (AP-3/AP-6, NR-9/NR-10) as executable
checks: identical inputs must yield byte-identical artifacts, independent of order
or environment.
"""

from __future__ import annotations

import pytest

from datasets._canonical import canonical_json, sha256_file
from datasets.ingestion import ingest_edf_file
from datasets.tests._edf_fixtures import standard_eeg_spec, write_edf


@pytest.mark.reproducibility
def test_fixture_writer_is_byte_identical(tmp_path):
    spec = standard_eeg_spec(edf_plus=True)
    p1 = write_edf(tmp_path / "a.edf", spec)
    p2 = write_edf(tmp_path / "b.edf", spec)
    assert sha256_file(p1) == sha256_file(p2)


@pytest.mark.determinism
def test_ingestion_is_deterministic(make_edf):
    path = make_edf(edf_plus=True)
    r1 = ingest_edf_file(path)
    r2 = ingest_edf_file(path)
    # The full record serializes identically across runs.
    assert canonical_json(r1.to_dict()) == canonical_json(r2.to_dict())


@pytest.mark.determinism
def test_content_addressed_ids_are_stable(make_edf):
    path = make_edf(edf_plus=True)
    sha = sha256_file(path)
    record = ingest_edf_file(path)
    assert record.file_id == f"edf-{sha[:16]}"
    assert record.raw_file.content_sha256 == sha


@pytest.mark.reproducibility
def test_identical_content_different_path_same_identity(tmp_path):
    spec = standard_eeg_spec(edf_plus=True)
    a = write_edf(tmp_path / "site_a.edf", spec)
    b = write_edf(tmp_path / "site_b.edf", spec)
    ra = ingest_edf_file(a)
    rb = ingest_edf_file(b)
    # Same bytes => same content identity (path is provenance, not identity).
    assert ra.file_id == rb.file_id
    assert ra.patient_id == rb.patient_id
