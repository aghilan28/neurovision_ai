"""Tests for the record and dataset registries."""

from __future__ import annotations

import pytest

from datasets.ingestion import ingest_edf_file
from datasets.registry import DatasetRegistry, RecordRegistry
from datasets.registry.dataset_registry import RegistryError
from datasets.schemas.enums import DatasetStatus, QualityState, ValidationStatus


def test_record_registry_indexes_and_discovers(make_edf):
    rr = RecordRegistry()
    a = ingest_edf_file(make_edf("a.edf", edf_plus=True, patient_field="P-1 M 01-JAN-1970 A"))
    b = ingest_edf_file(make_edf("b.edf", edf_plus=True, patient_field="P-2 F 01-JAN-1980 B"))
    rr.register_record(a)
    rr.register_record(b)
    assert len(rr) == 2
    assert a.file_id in rr
    assert rr.has_content(a.raw_file.content_sha256)
    assert a.raw_file.content_sha256 in rr.known_sha256()
    assert len(rr.find_by_patient(a.patient_id)) == 1


def test_record_registry_persists_deterministically(make_edf, tmp_path):
    rr = RecordRegistry()
    rr.register_record(ingest_edf_file(make_edf(edf_plus=True)))
    p = tmp_path / "records.json"
    rr.save(p)
    first = p.read_bytes()
    RecordRegistry.load(p).save(p)
    assert p.read_bytes() == first


def test_dataset_registry_lifecycle(tmp_path):
    dr = DatasetRegistry()
    dr.register_dataset("ds1", name="ICU", owner="team", source="local", created_at="t0")
    dr.update_status("ds1", DatasetStatus.VALIDATED, updated_at="t1")
    dr.set_states("ds1", validation_state=ValidationStatus.PASSED, quality_state=QualityState.OK)
    dr.attach_version("ds1", "v1", record_count=3, patient_count=3, updated_at="t2")
    ds = dr.get("ds1")
    assert ds.status is DatasetStatus.VALIDATED
    assert ds.current_version == "v1"
    assert ds.record_count == 3
    assert dr.find_by_owner("team") == (ds,)
    assert dr.find_by_status(DatasetStatus.VALIDATED) == (ds,)


def test_dataset_registry_rejects_duplicate_and_bad_dependency():
    dr = DatasetRegistry()
    dr.register_dataset("ds1", name="A", owner="o", source="s")
    with pytest.raises(RegistryError):
        dr.register_dataset("ds1", name="A2", owner="o", source="s")
    with pytest.raises(RegistryError):
        dr.register_dataset("ds2", name="B", owner="o", source="s", dependencies=("missing",))
    with pytest.raises(RegistryError):
        dr.register_dataset("ds3", name="C", owner="o", source="s", dependencies=("ds3",))


def test_dataset_registry_dependency_allowed_when_present():
    dr = DatasetRegistry()
    dr.register_dataset("base", name="Base", owner="o", source="s")
    dr.register_dataset("derived", name="Derived", owner="o", source="s", dependencies=("base",))
    assert dr.dependencies_of("derived") == ("base",)


def test_dataset_registry_round_trip(tmp_path):
    dr = DatasetRegistry()
    dr.register_dataset("ds1", name="A", owner="o", source="s", created_at="t0")
    dr.attach_version("ds1", "v1", record_count=1, patient_count=1)
    p = tmp_path / "datasets.json"
    dr.save(p)
    reloaded = DatasetRegistry.load(p)
    assert reloaded.get("ds1").to_dict() == dr.get("ds1").to_dict()
