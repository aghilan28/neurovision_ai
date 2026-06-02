"""Tests for class-distribution analysis."""

from __future__ import annotations

from datasets.tests._edf_fixtures import EdfPlusAnnotation
from evaluation.dataset_intelligence.distributions import (
    analyze_class_distribution,
    map_annotation_text,
)
from evaluation.dataset_intelligence.schemas.enums import EegClass
from evaluation.dataset_intelligence.tests.conftest import RecordSpec


def test_label_mapping_keywords():
    assert map_annotation_text("Seizure onset") is EegClass.SEIZURE
    assert map_annotation_text("GPD run") is EegClass.GPD
    assert map_annotation_text("LRDA segment") is EegClass.LRDA
    assert map_annotation_text("background") is EegClass.BACKGROUND
    assert map_annotation_text("something weird") is EegClass.OTHER


def test_class_counts_from_annotations(cohort):
    report = analyze_class_distribution(cohort)
    counts = dict(report.class_distribution.counts)
    assert counts.get("seizure") == 1
    assert counts.get("gpd") == 1
    assert counts.get("lpd") == 1
    assert counts.get("background") == 1
    families = dict(report.family_distribution.counts)
    assert families.get("iic") == 2  # gpd + lpd


def test_labeled_record_fraction(cohort):
    report = analyze_class_distribution(cohort)
    # 3 of 4 records carry annotations.
    assert report.labeled_record_fraction == 0.75


def test_no_labels_is_info(make_records):
    records = make_records([
        RecordSpec("a", "P-1 M 01-JAN-1970 A", annotations=[]),
        RecordSpec("b", "P-2 F 01-JAN-1980 B", annotations=[]),
    ])
    report = analyze_class_distribution(records)
    assert report.class_distribution.total == 0
    assert any(f.code == "NO_CLASS_LABELS" for f in report.findings)


def test_high_imbalance_flagged(make_records):
    anns_many = [EdfPlusAnnotation(float(i) % 10, 0.5, "Seizure") for i in range(20)]
    records = make_records([
        RecordSpec("a", "P-1 M 01-JAN-1970 A", duration_s=20.0, annotations=anns_many),
        RecordSpec("b", "P-2 F 01-JAN-1980 B", annotations=[EdfPlusAnnotation(1.0, 0.5, "LPD")]),
    ])
    report = analyze_class_distribution(records)
    assert report.imbalance_ratio >= 10.0
    assert any(f.code == "HIGH_CLASS_IMBALANCE" for f in report.findings)
