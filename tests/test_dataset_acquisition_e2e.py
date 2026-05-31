"""Track 1 end-to-end: the full Real Dataset Platform deliverable.

Drives the complete chain over **actual EEG recordings** (the committed real EDF fixtures
laid out as CHB-MIT, no network):

    discover -> validate -> extract labels -> extract metadata -> build inventory ->
    track lineage -> score training readiness

and asserts the dataset reaches ``READY_FOR_TRAINING`` with real (non-synthetic) labels,
a verified lineage chain to the source, a verified immutable audit, and byte-identical
re-runs (determinism).
"""

from __future__ import annotations

from _track1_helpers import build_local_chb_mit

from backend.dataset_acquisition import (
    DatasetSource, LabelScheme, RealDatasetService, TrainingReadinessClass,
)
from ml.provenance import canonical_json


def test_full_real_dataset_platform_deliverable(tmp_path):
    build_local_chb_mit(str(tmp_path))
    svc = RealDatasetService(data_root=str(tmp_path))
    out = svc.integrate(DatasetSource.CHB_MIT, allow_download=False)

    # discovered + read from ACTUAL files
    assert len(out.connector_result.discovered_files) == 2
    assert all(r.parse_ok for r in out.connector_result.recordings)
    # validated
    assert out.validation.ok
    # real labels (no synthetic)
    assert out.label_verification.scheme == LabelScheme.CHB_MIT_SEIZURE
    assert out.label_verification.coverage == 1.0 and out.label_verification.n_classes == 2
    # metadata + inventory
    assert out.inventory.n_recordings == 2 and out.inventory.total_duration_seconds > 0
    # lineage Source -> ... -> Registry verifies; audit verifies
    assert svc.lineage.verify_chain(out.registry_lineage_id)
    assert svc.audit_log_for(out.dataset_id).verify()
    # the headline deliverable
    assert out.readiness.classification == TrainingReadinessClass.READY_FOR_TRAINING
    assert out.ready_for_training


def test_full_deliverable_is_deterministic(tmp_path):
    build_local_chb_mit(str(tmp_path))
    out1 = RealDatasetService(data_root=str(tmp_path)).integrate(DatasetSource.CHB_MIT)
    out2 = RealDatasetService(data_root=str(tmp_path)).integrate(DatasetSource.CHB_MIT)
    # the full serialized outcome reproduces byte-for-byte (no wall-clock / randomness)
    assert canonical_json(out1.to_dict()) == canonical_json(out2.to_dict())


def test_reports_are_deterministic(tmp_path):
    build_local_chb_mit(str(tmp_path))
    svc1 = RealDatasetService(data_root=str(tmp_path))
    r1 = svc1.reports(svc1.integrate(DatasetSource.CHB_MIT))
    svc2 = RealDatasetService(data_root=str(tmp_path))
    r2 = svc2.reports(svc2.integrate(DatasetSource.CHB_MIT))
    assert canonical_json(r1) == canonical_json(r2)
