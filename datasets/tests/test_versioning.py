"""Tests for checksums, manifests, version chain, change tracking, and audits."""

from __future__ import annotations

import pytest

from datasets.ingestion import ingest_edf_file
from datasets.versioning import (
    audit_manifest,
    build_manifest,
    checksum_file,
    diff_manifests,
    verify_checksum,
    verify_dataset_version,
)
from datasets.versioning.version_chain import VersionChainError, VersionedDataset


def _records(make_edf, n):
    out = []
    for i in range(n):
        path = make_edf(f"r{i}.edf", edf_plus=True, patient_field=f"P-{i} M 01-JAN-1970 P{i}")
        out.append(ingest_edf_file(path))
    return out


def test_checksum_matches(make_edf):
    path = make_edf(edf_plus=True)
    sha = checksum_file(path)
    assert verify_checksum(path, sha)
    assert not verify_checksum(path, "0" * 64)


def test_manifest_fingerprint_is_order_independent(make_edf):
    recs = _records(make_edf, 3)
    m1 = build_manifest("ds", "v1", recs)
    m2 = build_manifest("ds", "v1", list(reversed(recs)))
    assert m1.content_fingerprint == m2.content_fingerprint
    assert m1.record_count == 3
    assert m1.patient_count == 3


def test_manifest_dedupes_identical_content(make_edf):
    path = make_edf(edf_plus=True)
    rec = ingest_edf_file(path)
    manifest = build_manifest("ds", "v1", [rec, rec])
    assert manifest.record_count == 1


def test_version_chain_tracks_parent_and_diff(make_edf):
    recs = _records(make_edf, 3)
    chain = VersionedDataset("ds")
    m1 = build_manifest("ds", "v1", recs[:2])
    v1, d1 = chain.commit(m1, change_summary="initial")
    assert v1.parent_version is None
    assert len(d1.added_file_ids) == 2

    m2 = build_manifest("ds", "v2", recs)
    v2, d2 = chain.commit(m2, change_summary="add one")
    assert v2.parent_version == "v1"
    assert len(d2.added_file_ids) == 1
    assert len(d2.removed_file_ids) == 0


def test_version_chain_rejects_noop_commit(make_edf):
    recs = _records(make_edf, 2)
    chain = VersionedDataset("ds")
    chain.commit(build_manifest("ds", "v1", recs))
    with pytest.raises(VersionChainError):
        chain.commit(build_manifest("ds", "v2", recs))  # identical content


def test_version_chain_rejects_wrong_dataset(make_edf):
    recs = _records(make_edf, 1)
    chain = VersionedDataset("ds")
    with pytest.raises(VersionChainError):
        chain.commit(build_manifest("other", "v1", recs))


def test_audit_detects_content_substitution(make_edf):
    recs = _records(make_edf, 2)
    manifest = build_manifest("ds", "v1", recs)
    known = {r.file_id: r.raw_file.content_sha256 for r in recs}
    assert audit_manifest(manifest, known).ok

    # Substitute a hash -> mismatch must be detected.
    tampered = dict(known)
    first_id = next(iter(tampered))
    tampered[first_id] = "0" * 64
    report = audit_manifest(manifest, tampered)
    assert not report.ok
    assert any(i.code == "MANIFEST_CONTENT_MISMATCH" for i in report.issues)


def test_audit_detects_unknown_record(make_edf):
    recs = _records(make_edf, 1)
    manifest = build_manifest("ds", "v1", recs)
    report = audit_manifest(manifest, {})  # registry knows nothing
    assert not report.ok
    assert any(i.code == "MANIFEST_RECORD_UNKNOWN" for i in report.issues)


def test_audit_detects_fingerprint_tampering(make_edf):
    recs = _records(make_edf, 2)
    chain = VersionedDataset("ds")
    version, _ = chain.commit(build_manifest("ds", "v1", recs))

    # A different manifest content must fail fingerprint verification.
    other = build_manifest("ds", "v1", recs[:1])
    assert not verify_dataset_version(version, other)
    report = audit_manifest(other, {recs[0].file_id: recs[0].raw_file.content_sha256}, version=version)
    assert any(i.code == "FINGERPRINT_MISMATCH" for i in report.issues)


def test_diff_against_empty_is_all_added(make_edf):
    recs = _records(make_edf, 2)
    manifest = build_manifest("ds", "v1", recs)
    diff = diff_manifests(None, manifest)
    assert len(diff.added_file_ids) == 2
    assert diff.removed_file_ids == ()
