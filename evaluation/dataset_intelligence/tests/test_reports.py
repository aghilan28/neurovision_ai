"""Tests for comprehensive report assembly, reproducibility, and persistence."""

from __future__ import annotations

import json

from evaluation._canonical import canonical_json
from evaluation.dataset_intelligence.reports import generate_intelligence_report, save_report


def test_comprehensive_report_has_all_sections(cohort):
    report = generate_intelligence_report(cohort, dataset_id="ds", dataset_version="v1")
    assert report.profile.n_recordings == 4
    assert report.patient.n_patients == 3
    assert report.channel.inventory
    assert report.recording.distinct_sampling_rates == 2
    assert report.class_distribution.class_distribution.total == 4
    assert 0.0 <= report.quality.quality_score <= 1.0
    assert report.leakage.leakage_risk_score >= 0.0
    assert report.summary["n_patients"] == 3


def test_report_is_timestamp_independent_reproducible(cohort):
    a = generate_intelligence_report(cohort, dataset_version="v1", generated_at="t1")
    b = generate_intelligence_report(cohort, dataset_version="v1", generated_at="t2")
    assert a.content_fingerprint == b.content_fingerprint


def test_sub_report_fingerprints_recorded(cohort):
    report = generate_intelligence_report(cohort)
    fps = report.to_dict()["sub_report_fingerprints"]
    assert set(fps) == {
        "profile", "patient", "channel", "recording",
        "class_distribution", "quality", "leakage",
    }
    assert fps["profile"] == report.profile.content_fingerprint


def test_save_report_is_deterministic(cohort, tmp_path):
    report = generate_intelligence_report(cohort, dataset_version="v1", generated_at="fixed")
    p = tmp_path / "report.json"
    save_report(report, p)
    first = p.read_bytes()
    save_report(report, p)
    assert p.read_bytes() == first
    # Round-trips through JSON.
    loaded = json.loads(p.read_text())
    assert loaded["provenance"]["intelligence_version"]


def test_input_fingerprint_changes_with_content(cohort, make_records):
    from evaluation.dataset_intelligence.tests.conftest import RecordSpec

    other = make_records([RecordSpec("x", "P-9 M 01-JAN-1965 X")])
    a = generate_intelligence_report(cohort)
    b = generate_intelligence_report(other)
    assert a.provenance.input_fingerprint != b.provenance.input_fingerprint
    assert canonical_json(a.to_dict()) != canonical_json(b.to_dict())
